import collections
from math import factorial
import os, os.path

import matplotlib.pyplot as plt
import pandas as pd
from pandas.tools.plotting import table


compare = lambda x, y: collections.Counter(x) == collections.Counter(y)

hand = [2, 3 ,6 ,2 ,2]

prob_dict = {
    "5Uguali": 6 / pow(6, 5),
    "4Uguali": 150 / pow(6, 5),
    "scala": 240 / pow(6, 5),
    "full": 300 / pow(6, 5),
    "tris": 1200 / pow(6, 5),
    "doppiaCoppia": 1800 / pow(6, 5),
    "coppia": 3600 / pow(6, 5),
}

def lists(my_dict, values, keys):
    for val in my_dict.values():
        if val not in values: values.append(val)
    values.sort(reverse=True)

    for key in my_dict.keys():
        if key not in keys: keys.append(key)
    keys.sort(reverse=True)


def calc_score(hand):
    my_dict = {i: hand.count(i) for i in hand}
    values = []
    keys = []
    lists(my_dict,values,keys)


    # 5 uguali
    if (values[0] == 5):
        flag = "5Uguali"
        #print(flag)

        num = 6 - get_key_by_value(my_dict, 5)
        if (num == 0): return 0
        return num/7776

    # 4 uguali
    if (values[0] == 4):
        flag = "4Uguali"
        #print(flag)

        higher_score_prob = prob_dict["5Uguali"]

        num = 6 - get_key_by_value(my_dict, 4)
        higher_score_prob_same = factorial(5) / factorial(4) * factorial(num) / factorial(4)
        return (higher_score_prob_same / 7776 + higher_score_prob)

    # scala 1->5
    if compare([1, 2, 3, 4, 5], hand):
        flag = "scala"
        #print(flag)

        higher_score_prob = prob_dict["5Uguali"] + prob_dict["4Uguali"]
        return higher_score_prob

    # scala 2->6
    if compare([6, 2, 3, 4, 5], hand):
        flag = "scala"
        #print(flag)

        higher_score_prob = prob_dict["5Uguali"] + prob_dict["4Uguali"] + prob_dict["scala"]
        return higher_score_prob

    # full
    if (len(values) == 2 and len(keys) == 2):
        flag = "full"
        #print(flag)

        higher_score_prob = prob_dict["5Uguali"] + prob_dict["4Uguali"] + prob_dict["scala"]
        num = (6 - get_key_by_value(my_dict, 3))
        higher_score_prob_same = 6 * 5 * factorial(num) / (2 * factorial(3))
        return higher_score_prob + higher_score_prob_same / 7776

    # tris
    if (3 in values):
        flag = "tris"
        #print(flag)

        higher_score_prob = prob_dict["5Uguali"] + prob_dict["4Uguali"] + prob_dict["scala"] + prob_dict["full"]
        num = (6 - get_key_by_value(my_dict, 3))
        higher_score_prob_same = factorial(5) / factorial(3) * factorial(num) / (factorial(3) * factorial(2))
        return higher_score_prob + higher_score_prob_same / 7776

    # doppia coppia
    if (len(keys) == 3 and 2 in values):
        flag = "doppiaCoppia"
        #print(flag)

        higher_score_prob = prob_dict["5Uguali"] + prob_dict["4Uguali"] + prob_dict["scala"] + prob_dict["full"] \
                            + prob_dict["tris"]
        num = 6 - get_key_by_value(my_dict, 2)
        higher_score_prob_same = factorial(5) / 4 * factorial(num) / 4
        return higher_score_prob + higher_score_prob_same / 7776

    # coppia
    if (len(keys) == 4 and 2 in values):
        flag = "coppia"
        #print(flag)

        higher_score_prob = prob_dict["5Uguali"] + prob_dict["4Uguali"] + prob_dict["scala"] + prob_dict["full"] \
                            + prob_dict["tris"] + prob_dict["doppiaCoppia"]
        num = 6 - get_key_by_value(my_dict, 2)

        higher_score_prob_same = factorial(5) / 2 * factorial(num) / (2 * factorial(3))
        return higher_score_prob_same / 7776 + higher_score_prob

    else:
        flag = "tutti diversi"
        #print(flag)

        return (prob_dict["5Uguali"] + prob_dict["4Uguali"] + prob_dict["scala"] + prob_dict["full"] \
                + prob_dict["tris"] + prob_dict["doppiaCoppia"] + prob_dict["coppia"])

def change_elem(lst, old_val, new_val):
    new_lst=list(lst)
    for index, item in enumerate(new_lst):
        if item==old_val:
            new_lst[index]=new_val
            break
    return new_lst


def combinazioni(n, k):
    return factorial(n) / (factorial(k) * factorial(n - k))


def get_key_by_value(dic, val):
    res = [k for k, v in dic.items() if v == val]
    if (len(res) == 1):
        return res[0]
    if (len(res) > 1):
        return min(res)
    else:
        print("error")
        print(dic,val)

def consigliami(hand):
    my_dict = {i: hand.count(i) for i in hand}
    values = []
    keys = []

    lists(my_dict, values, keys)
    current_score = (1 - calc_score(hand)) * 100

    table_lst=[]
    titolo=["Cambi", "Nuova %", "Vecchia %", "De/Incremento"]
    table_lst.append(titolo)
    df=pd.DataFrame(columns=titolo)



    # 5 uguali
    if (values[0] == 5):
        print("Non cambiare per nessun motivo!")
        return 0

    # 4 uguali
    elif (values[0] == 4):

        for i in range(1,7):
            new_good_score=(1-calc_score(change_elem(hand,get_key_by_value(my_dict,1),i)))*100
            row=[str(get_key_by_value(my_dict,1))+"->"+str(i),"{:.3f}".format(new_good_score),"{:.3f}".format(current_score),
                       "{:.3f}".format(new_good_score-current_score)]
            table_lst.append(row)
            df.loc[i]=row


    elif compare([1, 2, 3, 4, 5], hand):
        print("Non cambiare, puoi solo rimetterci!")
        return 0

    elif compare([6, 2, 3, 4, 5], hand):
        for i in range(1, 7):
            new_good_score = (1 - calc_score(change_elem(hand, 6, i))) * 100
            row = [ "6->" + str(i), "{:.3f}".format(new_good_score),
                   "{:.3f}".format(current_score),
                   "{:.3f}".format(new_good_score - current_score)]
            table_lst.append(row)
            df.loc[i] = row



    # full
    elif (len(values) == 2 and len(keys) == 2):

        for i in range(1,7):
            new_good_score=(1-calc_score(change_elem(hand, get_key_by_value(my_dict,2), i)))*100
            row=[str(get_key_by_value(my_dict,2))+"->"+str(i),"{:.3f}".format(new_good_score),"{:.3f}".format(current_score),
                           "{:.3f}".format(new_good_score-current_score)]
            table_lst.append(row)
            df.loc[i]=row



    # tris
    elif (3 in values):

        for i in range(1,7):
            new_good_score=(1-calc_score(change_elem(hand, get_key_by_value(my_dict,1), i)))*100
            row=[str(get_key_by_value(my_dict, 1))+"->"+str(i), "{:.3f}".format(new_good_score), "{:.3f}".format(current_score),
                       "{:.3f}".format(new_good_score - current_score)]
            table_lst.append(row)
            df.loc[i]=row



    # doppia coppia
    elif (len(keys) == 3 and 2 in values):

        for i in range(1,7):
            new_good_score = (1 - calc_score(change_elem(hand, get_key_by_value(my_dict, 1), i))) * 100
            row=[str(get_key_by_value(my_dict, 1))+"->"+str(i), "{:.3f}".format(new_good_score), "{:.3f}".format(current_score),
                       "{:.3f}".format(new_good_score - current_score)]
            table_lst.append(row)
            df.loc[i]=row



    # coppia
    elif (len(keys) == 4 and 2 in values):
        for i in range(1,7):
            new_good_score = (1 - calc_score(change_elem(hand, get_key_by_value(my_dict, 2), i))) * 100
            row=[str(get_key_by_value(my_dict, 2))+"->"+str(i), "{:.3f}".format(new_good_score), "{:.3f}".format(current_score),
                           "{:.3f}".format(new_good_score - current_score)]
            table_lst.append(row)
            df.loc[i]=row



        for i in range(1,7):
            new_good_score = (1 - calc_score(change_elem(hand, get_key_by_value(my_dict, 1), i))) * 100
            row=[str(get_key_by_value(my_dict,1))+"->"+str(i), "{:.3f}".format(new_good_score), "{:.3f}".format(current_score),
                           "{:.3f}".format(new_good_score - current_score)]
            table_lst.append(row)
            df.loc[i+6]=row



    else:
        for i in range(1, 7):
            new_good_score = (1 - calc_score(change_elem(hand, 1, i))) * 100
            row=["1->"+str(i), "{:.3f}".format(new_good_score), "{:.3f}".format(current_score),
                           "{:.3f}".format(new_good_score - current_score)]
            table_lst.append(row)
            df.loc[i]=row


        for i in range(1, 7):
            new_good_score = (1 - calc_score(change_elem(hand, 6, i))) * 100
            row=["6->"+str(i), "{:.3f}".format(new_good_score), "{:.3f}".format(current_score),
                           "{:.3f}".format(new_good_score - current_score)]
            table_lst.append(row)
            df.loc[i]=row


    #print(df)
    ax = plt.subplot(111, frame_on=False)  # no visible frame
    ax.xaxis.set_visible(False)  # hide the x axis
    ax.yaxis.set_visible(False)  # hide the y axis

    table(ax, df,rowLabels=['']*df.shape[0], loc='center')  # where df is your data frame
    path="tables/"
    i=len([f for f in os.listdir(path)  if os.path.isfile(os.path.join(path, f))])
    path_save_name='tables/mytable'+str(i)+".png"

    plt.savefig(path_save_name)
    return path_save_name


#print((1-calc_score(hand))*100)
#consigliami(hand)



