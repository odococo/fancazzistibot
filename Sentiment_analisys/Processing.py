import time
from os import system

import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.svm import LinearSVC, SVC

from Sentiment_analisys.util import *
from Sentiment_analisys.Preprocessing import *
from Sentiment_analisys.Data_analisys import *

TO_PLOT = False
TO_SAVE_WRONG=False
TO_PRED=True

def SVC_classifier(train_set_labled, train_set_unlabled, test_set):
    # Data pre processing
    xtrain_vec, xtest_vec, ytrain, names = polish_tfidf_kbest(train_set_labled, train_set_unlabled, test_set)

    print("Executing classification......")
    start = time.time()

    # classifier initialization and fitting
    #svc = LinearSVC(verbose=True, penalty="l2", loss="hinge",multi_class="ovr",C=1)
    svc = SVC(verbose=True, kernel="linear",decision_function_shape="ovr",C=1)
    svc = svc.fit(xtrain_vec, ytrain)

    end = time.time()
    tot = end - start
    print("fitting completed\nTotal time: " + str(int(tot / 60)) + "' " + str(int(tot % 60)) + "''\n")

    if TO_PLOT:
        #plot_svm_dataset(xtrain_vec, ytrain, svc)
        # plot_svm_vect(svc)
        plot_svm_decision_boundary(svc,xtest_vec,test_set["sentiment"])


    if TO_PRED:
        # prediction
        pred_forest = svc.predict(xtest_vec)
        scoring(pred_forest,test_set["sentiment"],"Test set",svc)



    if(TO_SAVE_WRONG):
     #saving wrong prediction for analysis
        save_wrong_answer(pred_forest,names,xtest_vec)

    return svc

def predict(classfier, train_set_labled, train_set_unlabled, test_set):
    # Data pre processing
    xtrain_vec, xtest_vec, ytrain, names = polish_tfidf_kbest(train_set_labled, train_set_unlabled, test_set)
    pred=classfier.predict(xtest_vec)
    return pred

# def multiple_classifier(*models):
#     xtrain_vec, xtest_vec, ytrain, names = polish_tfidf_kbest(TRAIN_DATASET_LABLED,
#                                                                    TRAIN_DATASET_UNLABLED, TEST_DATASET)
#
#     for model in models:
#         print("Executing fitting for " + str(model))
#         model.fit(xtrain_vec, ytrain)
#         pred = model.predict(xtest_vec)
#         scoring(pred,TEST_DATASET["sentiment"],"null",model)


def forest_classifier(train_set_labled, train_set_unlabled, test_set):
    # Data pre processing
    xtrain_vec, xtest_vec, ytrain, names = polish_tfidf_kbest(train_set_labled, train_set_unlabled, test_set)

    print("Executing classification......")
    start = time.time()

    # classifier initialization and fitting
    forest = RandomForestClassifier(n_estimators=250, n_jobs=-1, verbose=1, criterion="entropy")
    forest = forest.fit(xtrain_vec, ytrain)

    end = time.time()
    tot = end - start
    print("fitting completed\nTotal time: " + str(int(tot / 60)) + "' " + str(int(tot % 60)) + "''\n")

    if TO_PLOT:
        #plot_forest_vect(forest)
        plot_trees(forest.estimators_,names)
        #plot_top_forest(forest, names, 20)

    if TO_PRED:
        # prediction
        pred_forest = forest.predict(xtest_vec)
        scoring(pred_forest,test_set["sentiment"],"Test Set",forest)




    if TO_SAVE_WRONG:
        save_wrong_answer(pred_forest,names,xtest_vec)

    return forest
