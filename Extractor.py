import requests
import pandas as pd
import numpy as np
from tqdm import tqdm
from typing import Tuple
import argparse

class Extractor():
    """Provide token if you have generated any
    """
    def __init__(self,token: str="", sample: int=50):
        self.token=token
        self.sample=sample

    def jsonExtractor(self, category: str=None, handle: str=None) -> dict:
        """ json extractor follow `https://github.com/Exodus-Privacy/exodus/blob/v1/doc/api.md` for more.

        :param category: either `application` or `tracker` to get json data
        :param handle: specific app handle name (ex: com.instagram.android)
        """
        auth = ('Token',self.token)
        try:
            if category is not None:
                if category=='application':
                    print("fetching application data from exodus server...")
                    url = 'https://reports.exodus-privacy.eu.org/api/applications'
                    return requests.get(url,auth=auth).json()
                if category=='tracker':
                    print("fetching tracker data from exodus server...")
                    url = 'https://reports.exodus-privacy.eu.org/api/trackers'
                    return requests.get(url,auth=auth).json()
                else:
                    raise KeyError(category)
                    
            if handle is not None:
                print("fetching detailed application and associated tracker data from exodus server...")
                url = 'https://reports.exodus-privacy.eu.org/api/search/{}'.format(handle)
                return requests.get(url,auth=auth).json()
            else:
                raise KeyError("Needed either category or handle parameter")
        except:
            return {}

    def prepareData(self) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """ Prepares the application and tracker table.
        Notations followed as displayed in `https://github.com/Exodus-Privacy/exodus/blob/v1/doc/api.md`.
        """   
        apps = self.jsonExtractor(category = 'application')
        app_data = pd.DataFrame(data=[pd.Series([x.get('handle') for x in apps['applications']], name='handle'),
                                    pd.Series([x.get('name') for x in apps['applications']], name='app_name')]).transpose()
        app_data['app_name'] = app_data.app_name.apply(lambda x: x if len(x)>1 else 'NOT PROVIDED')

        trackers = self.jsonExtractor(category = 'tracker')
        tracker_data = pd.DataFrame(pd.Series(trackers['trackers']).apply(pd.Series),columns = ['id','name','creation_date'])
        tracker_data['creation_date'] = tracker_data.creation_date.astype('datetime64[ns]')
        tracker_data.rename(columns={'name':'tracker_name','id':'tracker_id'},inplace=True)

        app_data.set_index('handle',inplace=True)
        tracker_data.set_index('tracker_id',inplace=True)

        return app_data, tracker_data


    def accumulateAll(self, app: pd.DataFrame, tracker: pd.DataFrame) -> pd.DataFrame:
        """ Function call to prepare the dataset. (Needed application and tracker data set)
        call :func:`prepareData` before calling this function.

        :param app: Application data
        :param tracker: tracker data
        :return: A dataset.

        """

        print("Considering only {} sample of applications. (Might take some time ! ! !)".format(self.sample))
        app_data = app.sample(self.sample)

        ## detailed extraction
        df=pd.DataFrame()
        for x in tqdm(app_data.index):
            try:
                data = self.jsonExtractor(handle=x)[x]
                temp = pd.DataFrame(data.get('reports')[0])[['version','updated_at', 'trackers', 'downloads']]
                temp['handle'] = x
            except KeyError:
                continue
            df = pd.concat([df,temp],axis=0)
        df.rename(columns={'trackers':'tracker_id'},inplace=True)
        df['tracker_id'] = df.tracker_id.astype('int')

        df= df.set_index('tracker_id').join(tracker,how='left').reset_index()
        final = df.set_index('handle').join(app_data,how='left').reset_index().sort_values(by='handle')
        return final


if __name__=="__main__":
    parser = argparse.ArgumentParser(description='Basic data accumulator script on "Exodus Privacy" report.')
    parser.add_argument("output", help="output file name [Needed: *.csv]")
    parser.add_argument("--token",'-t',dest='token', help="provide your generated token (If any)")
    parser.add_argument("--sample",'-s',dest='sample', type=int, help="Provide a random sampling value to bypass run on all application")
    args = parser.parse_args()

    assert args.output.split(".")[-1]=='csv',"Provide .csv format file name"
    
    ## Manipulate at command-line level
    ## Add your own token
    ## Provide a random sampling value
    if args.token:
        token = args.token

    if args.sample:
        sample = args.sample

    ## Call
    data_file = Extractor(token="9944b09199c62bcf9418ad846dd0e4bbdfc6ee4b",sample=70)
    app_data, tracker_data = data_file.prepareData()
    result = data_file.accumulateAll(app_data,tracker_data)

    result.to_csv(args.output)
    print("Dataset generated...\n{}".format("#\n*5"))





