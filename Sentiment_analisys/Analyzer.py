import math
import pandas as pd

from Sentiment_analisys.Processing import SVC_classifier, forest_classifier, predict


class Analyzer:


    def __init__(self, data_list_labled,data_list_unlabled, train_size_perc=0.6):

        size=len(data_list_labled)
        train_size=math.ceil(size*train_size_perc)

        self.TRAIN_SET_LABLED=pd.DataFrame(data_list_labled[:train_size])
        self.TEST_SET=pd.DataFrame(data_list_labled[train_size+1:])
        self.TRAIN_SET_UNLABLED=pd.DataFrame(data_list_unlabled)

        self.svc=None
        self.forest=None


    def train_models(self):

        self.svc=SVC_classifier(self.TRAIN_SET_LABLED,self.TRAIN_SET_UNLABLED,self.TEST_SET)
        self.forest=forest_classifier(self.TRAIN_SET_LABLED,self.TRAIN_SET_UNLABLED,self.TEST_SET)


    def predict(self, text):
        if not self.svc or not self.forest:
            return None

        print("predicting")
        text=[{'review':elem['content']} for elem in text]
        text=pd.DataFrame(text)
        pred_svc=predict(self.svc,self.TRAIN_SET_LABLED,text,self.TEST_SET)
        pred_forest=predict(self.forest,self.TRAIN_SET_LABLED,text,self.TEST_SET)

        print(pred_svc)
        print(pred_forest)