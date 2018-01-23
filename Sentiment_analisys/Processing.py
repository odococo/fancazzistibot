import time
from os import system

import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import SGDClassifier
from sklearn.svm import LinearSVC, SVC

from Sentiment_analisys.util import *
from Sentiment_analisys.Preprocessing import *
from Sentiment_analisys.Data_analisys import *

TO_PLOT = False
TO_SAVE_WRONG=False
TO_PRED=True

class Processing:

    def __init__(self):

        self.svc=SVC(verbose=True, kernel="sigmoid",decision_function_shape="ovr",C=1,gamma=2)
        self.sgdc=SGDClassifier(loss="hinge", penalty="l2")
        self.preprocessing=Preprocessing()

    def SVC_classifier(self,train_set_labled, train_set_unlabled, test_set):
        # Data pre processing
        xtrain_vec, xtest_vec, ytrain, names =  self.preprocessing.polish_tfidf_kbest(train_set_labled, train_set_unlabled, test_set)

        print("Executing classification......")
        start = time.time()

        # classifier initialization and fitting
        #svc = LinearSVC(verbose=True, penalty="l2", loss="hinge",multi_class="ovr",C=1)
        #svc = SVC(verbose=True, kernel="linear",decision_function_shape="ovr",C=1)
        self.svc = self.svc.fit(xtrain_vec, ytrain)

        end = time.time()
        tot = end - start
        print("fitting completed\nTotal time: " + str(int(tot / 60)) + "' " + str(int(tot % 60)) + "''\n")



        if TO_PRED:
            # prediction
            pred_forest = self.svc.predict(xtest_vec)
            print("=========PREDICTION=============\n"+str(pred_forest))
            scoring(pred_forest,test_set["sentiment"],"SVC",self.svc)



        if(TO_SAVE_WRONG):
         #saving wrong prediction for analysis
            save_wrong_answer(pred_forest,names,xtest_vec)



    def SGDC(self,train_set_labled, train_set_unlabled, test_set):
        # Data pre processing
        xtrain_vec, xtest_vec, ytrain, names = self.preprocessing.polish_tfidf_kbest(train_set_labled, train_set_unlabled, test_set)

        print("Executing classification......")
        start = time.time()

        # classifier initialization and fitting
        #svc = LinearSVC(verbose=True, penalty="l2", loss="hinge",multi_class="ovr",C=1)
        #svc = SVC(verbose=True, kernel="linear",decision_function_shape="ovr",C=1)
        self.sgdc = self.sgdc.fit(xtrain_vec, ytrain)

        end = time.time()
        tot = end - start
        print("fitting completed\nTotal time: " + str(int(tot / 60)) + "' " + str(int(tot % 60)) + "''\n")


        if TO_PRED:
            # prediction
            pred_forest = self.sgdc.predict(xtest_vec)
            scoring(pred_forest, test_set["sentiment"],"SGDC", self.sgdc)





    def predict(self,classfier, train_set_labled, train_set_unlabled, test_set):
        # Data pre processing
        xtrain_vec, xtest_vec, ytrain, names =  self.preprocessing.polish_tfidf_kbest(train_set_labled, train_set_unlabled, test_set)
        pred=classfier.predict(xtest_vec)
        return pred


    def forest_classifier(self,train_set_labled, train_set_unlabled, test_set):
        # Data pre processing
        xtrain_vec, xtest_vec, ytrain, names =  self.preprocessing.polish_tfidf_kbest(train_set_labled, train_set_unlabled, test_set)

        print("Executing classification......")
        start = time.time()

        # classifier initialization and fitting
        forest = RandomForestClassifier(n_estimators=250, n_jobs=-1, verbose=1, criterion="entropy")
        forest = forest.fit(xtrain_vec, ytrain)

        end = time.time()
        tot = end - start
        print("fitting completed\nTotal time: " + str(int(tot / 60)) + "' " + str(int(tot % 60)) + "''\n")


        if TO_PRED:
            # prediction
            pred_forest = forest.predict(xtest_vec)
            scoring(pred_forest,test_set["sentiment"],"Test Set",forest)



        return forest
