from os import system
import os
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import GridSearchCV
from sklearn.model_selection import cross_val_score
from sklearn.svm import LinearSVC

from Sentiment_analisys.Preprocessing import *


def cross_validation_score(model, x,test_dataset):
    scores = cross_val_score(model, x, y=test_dataset["sentiment"])
    print(scores)


def scoring(prediction, true, what, clf):

    #using mean square error for calculating accurancy
    pred = str(np.mean(prediction == true) * 100)
    #printing score
    print("Score for "+what+" is: " + pred)
    string = "Score is " + pred + " percent"
    system('say ' + string)

    with open (os.getcwd() + "/src/best_score.txt") as file:
        best_score=file.readline().split(",")[0]

    if(pred>best_score):
        with open(os.getcwd() + "/src /best_score.txt","w") as file:
            file.write(pred+", "+clf.__str__())

def polish_tfidf_kbest(train_set_labled, train_set_unlabled, test_set):
    # splitting  train test
    xtrainL = train_set_labled["review"]
    xtrainU = train_set_unlabled["review"]
    xtest = test_set["review"]
    ytrain = train_set_labled["sentiment"]

    print("Starting trasformation from string to vector...")

    # transforming to vector
    xtrain_vec, xtest_vec, vect = string2vecTFIDF(xtrainL, xtrainU, xtest)

    feature_names = vect.get_feature_names()

    print("Executing chi2 test...")

    reduced_xtrain_vec, reduced_xtest_vec = dimensionality_reductionKB(xtrain_vec, ytrain, xtest_vec,feature_names)
    return reduced_xtrain_vec, reduced_xtest_vec, ytrain, feature_names

def grid(xtrain, ytrain):
    svm = LinearSVC(verbose=True, penalty="l2", loss="hinge",multi_class="ovr")

    param = {"C": [1, 2]}

    grid = GridSearchCV(svm, param, n_jobs=-1, verbose=1, error_score=-1)
    grid.fit(xtrain, ytrain)

    print(grid.best_estimator_)
    print(grid.best_score_)
    print(grid.best_params_)

def save_wrong_answer(pred,names,xtest,test_dataset):

    # n is the number of feature to print
    n=3


    # saving true values
    true=test_dataset["sentiment"]
    wrong=[]

    idx=0
    index=[]

    # for every cuple (predicted, true value)
    for i,j in zip(pred,true):
        # if values are not the same
        if (i!=j):
            # adding i-th review to the list plus incorrect prediction
            wrong.append((idx,test_dataset["review"].iget(idx),i))
            # saving indices of wrong prediction
            index.append(idx)
        idx+=1


    # saving file with wrong prediction for further analysis
    with open(os.getcwd() + "/wrong.txt","w") as file:
        file.write('\n\n'.join('%d) %s \t Incorrect= %s' % x for x in wrong))

    print("wrong file saved")

    # taking all missclassified reviews
    samples=[]
    for elem in index:
        samples.append(xtest[elem])

    # for evrey misscalssified review, take corresponding features values
    correct=[]
    for line in samples:
        # linking features with words
        line=[y for y in zip(line,names)]
        # taking top-n features
        line=sorted(line,key= lambda tup: tup[0])[-n:]
        # appending to list
        correct.append(line)


    anlayzer=[]
    idx=0
    # analyzer have this form (index, (value, word))
    for elem in index:
        anlayzer.append((elem,correct[idx]))
        idx+=1

        # save file
    with open(os.getcwd() + "/wrong_data.txt", "w") as file:
        file.write('\n\n'.join('%d) %s' % x for x in anlayzer))

    print("wrong_data file created")


