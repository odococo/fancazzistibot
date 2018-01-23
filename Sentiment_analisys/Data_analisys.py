import operator
import time
from math import ceil
from math import isnan

import matplotlib.pyplot as plt
import numpy as np
from os import system
from sklearn.feature_selection import chi2
from sklearn.model_selection import learning_curve
from sklearn.tree import export_graphviz


## Generic
def plot_learning_curve(estimator, title, X, y, ylim=None, cv=None,
                        n_jobs=1, train_sizes=np.linspace(.1, 1.0, 5)):
    """
    Generate a simple plot of the test and training learning curve.

    Parameters
    ----------
    estimator : object type that implements the "fit" and "predict" methods
        An object of that type which is cloned for each validation.

    title : string
        Title for the chart.

    X : array-like, shape (n_samples, n_features)
        Training vector, where n_samples is the number of samples and
        n_features is the number of features.

    y : array-like, shape (n_samples) or (n_samples, n_features), optional
        Target relative to X for classification or regression;
        None for unsupervised learning.

    ylim : tuple, shape (ymin, ymax), optional
        Defines minimum and maximum yvalues plotted.

    cv : int, cross-validation generator or an iterable, optional
        Determines the cross-validation splitting strategy.
        Possible inputs for cv are:
          - None, to use the default 3-fold cross-validation,
          - integer, to specify the number of folds.
          - An object to be used as a cross-validation generator.
          - An iterable yielding train/test splits.

        For integer/None inputs, if ``y`` is binary or multiclass,
        :class:`StratifiedKFold` used. If the estimator is not a classifier
        or if ``y`` is neither binary nor multiclass, :class:`KFold` is used.

        Refer :ref:`User Guide <cross_validation>` for the various
        cross-validators that can be used here.

    n_jobs : integer, optional
        Number of jobs to run in parallel (default 1).
    """
    plt.figure()
    plt.title(title)
    if ylim is not None:
        plt.ylim(*ylim)
    plt.xlabel("Training examples")
    plt.ylabel("Score")

    print("learning curve....")
    train_sizes, train_scores, test_scores = learning_curve(
        estimator, X, y, cv=cv, n_jobs=n_jobs, train_sizes=train_sizes, verbose=1)
    print("calculating means and std...")
    train_scores_mean = np.mean(train_scores, axis=1)
    train_scores_std = np.std(train_scores, axis=1)
    test_scores_mean = np.mean(test_scores, axis=1)
    test_scores_std = np.std(test_scores, axis=1)

    print("plotting...")
    plt.grid()

    plt.fill_between(train_sizes, train_scores_mean - train_scores_std,
                     train_scores_mean + train_scores_std, alpha=0.1,
                     color="r")
    plt.fill_between(train_sizes, test_scores_mean - test_scores_std,
                     test_scores_mean + test_scores_std, alpha=0.1, color="g")
    plt.plot(train_sizes, train_scores_mean, 'o-', color="r",
             label="Training score")
    plt.plot(train_sizes, test_scores_mean, 'o-', color="g",
             label="Cross-validation score")

    plt.legend(loc="best")
    plt.show()
    plt.imsave()
    return plt


##chi2
def plot_chi2_top(xtrain_vec, ytrain_vec, trans):
    print("Calculating chi2...")
    start = time.time()
    chi2_res = chi2(xtrain_vec, ytrain_vec)[0]
    end = time.time()
    print("Total time: " + str(end - start) + " seconds")

    # creating dictionary and sorting
    features = trans.get_feature_names()
    d = dict(zip(features, chi2_res))

    # deleting nan values
    d = {k: d[k] for k in d if not isnan(d[k])}

    sort = sorted(d.items(), key=operator.itemgetter(1), reverse=False)[:20]
    keys = [i[0] for i in sort]
    values = [int(i[1]) for i in sort]

    # calculating mean
    mean = 0
    for elem in values:
        mean += elem

    mean /= len(values)

    plt.figure()
    # setting title
    plt.title("Worst 20 features for chi2")

    # plotting data
    plt.bar(range(len(sort)), values, align='edge', color="green")
    plt.xticks([(x + 0.4) for x in range(len(sort))], keys, rotation=90, y=0.8, color="black", size="large")

    # plotting mean
    plt.axhline(y=mean, c="red")
    plt.text(0, mean, "mean: " + str(mean), color="red", size="large")

    plt.show()


def plot_chi2_vect(xtrain_vec, ytrain_vec):
    print("calculating chi2...")
    start = time.time()
    chi2_res = chi2(xtrain_vec, ytrain_vec)[0]
    end = time.time()
    print("Total time: " + str(end - start) + " seconds")

    sort = sorted(chi2_res)
    values = enumerate(sort)

    # saving max and min values
    min_value = int(min(sort))
    max_value = int(max(sort))

    # creating dictionary in which keys are values between min and max,
    values_dict = dict((elem, 0) for elem in range(min_value, max_value + 10, 10))

    # replacing nan values to zero
    sort = np.nan_to_num(sort)

    # counting how many elem in list are between range (min,max)
    for elem in sort:
       idx = int(ceil(elem / 10.0)) * 10
       values_dict[idx] += 1

    x, y = zip(*values)

    # setting title
    plt.figure(figsize=(10, 10))
    plt.title("All of " + str(len(sort)) + " words from chi2")

    # for every elem in dictionary, draw line and write value
    for elem in values_dict.keys():
       plt.axhline(y=elem, c="red")
       plt.text(-10000, elem, str(values_dict[elem]) + " words")

    plt.scatter(x, y)
    # plt.xticks(range(len(d)), d.keys(), rotation=90)
    plt.show()


## TFIDF

def plot_vector(trans):
    """Questa funzione prende in input un trasformatore( TFIDF o countVectorize), ne estrae i valori e li plotta
    dividento le ordinate in n parti, con n preso tra minimo e massimo tra i valori presenti. Inoltre stampe le parole
     presenti in ogni range di n valori"""

    # taking word's values
    idf = trans.idf_

    # sorting values and creating tuples list in which the first elem is index, second is value
    sort = sorted(idf)
    values = enumerate(sort)

    # saving min max values
    min_value = int(min(sort))
    max_value = int(max(sort))

    # creating dictionary in which keys are values between min and max,
    values_dict = dict((elem, 0) for elem in range(min_value, max_value + 1))

    # counting how many elem in list are between range (min,max)
    for elem in sort:
        values_dict[int(elem)] += 1

    x, y = zip(*values)

    # setting title
    plt.figure(figsize=(10, 10))
    plt.title("All of 70708 words from TFIDF")

    # for every elem in dictionary, draw line and write value
    for elem in values_dict.keys():
        plt.axhline(y=elem, c="red")
        plt.text(-10000, elem, str(values_dict[elem]) + " words")

    plt.scatter(x, y)
    plt.show()


def plot_top_n_words(trans, n, reverse=False):
    """Questa funzione prende in input 3 parametri, un trasformatore, un intero (si consiglia sotto i 50) e un boolean.
    La sua funzione è quella di plottare le n parole con punteggio piu altro (o piu basso dipende da reverse)"""

    # taking word's values
    idf = trans.idf_
    features = trans.get_feature_names()

    # creating dictionary
    d = dict(zip(features, idf))
    # taking top n values with best score
    sort = sorted(d.items(), key=operator.itemgetter(1), reverse=reverse)[:n]
    # reversing to dict to be plotted
    d = dict(sort)

    # calculating mean
    mean = 0
    for elem in d.values():
        mean += elem

    mean /= len(d)

    plt.figure()
    # choosing titile
    if (reverse):
        plt.title("Top " + str(n) + " features")
    else:
        plt.title("Worst " + str(n) + " features")

    # plotting data
    plt.bar(range(len(d)), d.values(), align='center')
    plt.xticks(range(len(d)), d.keys(), rotation=90, y=0.5, color="white")

    # plotting mean
    plt.axhline(y=mean, c="red")
    plt.text(0, mean, "mean: " + str(mean), color="red", size="large")

    plt.show()


##Forest

def plot_forest_vect(forest):
    features = forest.feature_importances_
    sort = sorted(features)
    to_plot = enumerate(sort)
    x, y = zip(*to_plot)

    plt.figure()
    plt.title("Forest distribution")

    plt.scatter(x, y)
    plt.show()


def plot_top_forest(forest, names, n):
    features = forest.feature_importances_
    zipped = zip(features, names)

    sort = sorted(zipped, key=lambda x: x[1])
    print(sort[:10])
    print(sort[-10:])

    keys = [i[1] for i in sort]
    values = [int(i[0]) for i in sort]

    # calculating mean
    mean = 0
    for elem in values:
        mean += elem

    mean /= len(values)

    plt.figure()
    # setting title
    plt.title("Top " + str(n) + " features for forest")

    # plotting data
    plt.bar(range(len(sort)), values, align='edge', color="green")
    plt.xticks([(x + 0.4) for x in range(len(sort))], keys, rotation=90, y=0.8, color="black", size="large")

    # plotting mean
    plt.axhline(y=mean, c="red")
    plt.text(0, mean, "mean: " + str(mean), color="red", size="large")

    plt.show()


def plot_trees(trees, columns_names):
    export_graphviz(trees[0],
                        feature_names=columns_names,
                        filled=True,
                        rounded=True)
    system('dot -Tpng tree.dot -o tree.png')


##SVM

def plot_svm_vect(svc):
    coef = svc.coef_
    sort = sorted(coef)
    to_plot = enumerate(sort)
    x, y = zip(to_plot)

    plt.figure()
    plt.title("SVC distribution")

    plt.scatter(x, y)
    plt.show()


def plot_svm_dataset(xtrain, ytrain, svm):
    h = .02  # step size in the mesh
    X = xtrain[:, :2]
    # create a mesh to plot in
    x_min, x_max = X[:, 0].min() - 1, X[:, 0].max() + 1
    y_min, y_max = X[:, 1].min() - 1, X[:, 1].max() + 1
    xx, yy = np.meshgrid(np.arange(x_min, x_max, h),
                         np.arange(y_min, y_max, h))

    # Plot the decision boundary. For that, we will assign a color to each
    # point in the mesh [x_min, x_max]x[y_min, y_max].
    plt.subplot(2, 2, 1)
    plt.subplots_adjust(wspace=0.4, hspace=0.4)

    Z = svm.predict(np.c_[xx.ravel(), yy.ravel()])

    # Put the result into a color plot
    Z = Z.reshape(xx.shape)
    plt.contourf(xx, yy, Z, cmap=plt.cm.coolwarm, alpha=0.8)

    # Plot also the training points
    plt.scatter(X[:, 0], X[:, 1], c=ytrain, cmap=plt.cm.coolwarm)
    plt.xlabel('Sepal length')
    plt.ylabel('Sepal width')
    plt.xlim(xx.min(), xx.max())
    plt.ylim(yy.min(), yy.max())
    plt.xticks(())
    plt.yticks(())
    plt.title("Svm dataset")

    plt.show()


def plot_top_svm(svm, names, n):
    features = svm.coef_
    zipped = zip(features, names)

    sort = sorted(zipped, key=lambda x: x[0])[-n:]

    keys = [i[1] for i in sort]
    values = [int(i[0]) for i in sort]

    # calcolo la media dei valori
    mean = 0
    for elem in values:
        mean += elem

    mean /= len(values)

    plt.figure()
    # setto il titolo
    plt.title("Top " + str(n) + " features for forest")

    # plotto i dati
    plt.bar(range(len(sort)), values, align='edge', color="green")
    plt.xticks([(x + 0.4) for x in range(len(sort))], keys, rotation=90, y=0.8, color="black", size="large")

    # plotto la media
    plt.axhline(y=mean, c="red")
    plt.text(0, mean, "mean: " + str(mean), color="red", size="large")

    plt.show()

def plot_svm_decision_boundary(clf, X,Y):

    # we create 40 separable points
    np.random.seed(0)
    # fit the model

    # get the separating hyperplane
    w = clf.coef_[0]
    a = -w[0] / w[1]
    xx = np.linspace(-5, 5)
    yy = a * xx - (clf.intercept_[0]) / w[1]

    # plot the parallels to the separating hyperplane that pass through the
    # support vectors
    b = clf.support_vectors_[0]
    yy_down = a * xx + (b[1] - a * b[0])
    b = clf.support_vectors_[-1]
    yy_up = a * xx + (b[1] - a * b[0])

    # plot the line, the points, and the nearest vectors to the plane
    plt.plot(xx, yy, 'k-')
    plt.plot(xx, yy_down, 'k--')
    plt.plot(xx, yy_up, 'k--')

    plt.scatter(clf.support_vectors_[:, 0], clf.support_vectors_[:, 1],
                s=80, facecolors='none')
    plt.scatter(X[:, 0], X[:, 1], c=Y, cmap=plt.cm.Paired)

    plt.axis('tight')
    plt.show()
