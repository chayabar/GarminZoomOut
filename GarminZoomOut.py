import glob
import json
import pathlib
import sys
from collections import Counter
from datetime import datetime

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

# ----------------- directories and files -----------------
out_dir = str(pathlib.Path(__file__).parent.resolve()) + '/'
file_path = glob.glob(out_dir + '**/*summarizedActivities.json', recursive=True)
if len(file_path) == 0:
    print("Sorry! We didn't find the data file with the suffix 'summarizedActivities.json'."
          "\nPlease ensure that the downloaded data is in the scripts folder")
    exit()
else:
    file_path = file_path[0]


# ------------------- functions -------------------


def get_dict():
    d = {'lap_swimming': {'d': [], 'avgHr': [], 'avgLapTime': [], 'avgStrokes': []},
         'running': {'d': [], 'avgHr': [], 'Duration': [], 'avgPace': [], 'avgDoubleCadence': []},
         'walking': {'d': [], 'avgHr': [], 'Duration': [], 'Distance': [], 'avgPace': []}}
    return d


# explanation of how to use this script
def help_doc():
    print('Usage: python GarminZoomOut.py [Options]...\n' +
          'Analyze Garmin activity data\n' +
          "Mandatory: Garmin data (folder/file) should be in the script's directory. The script recognize it according to the suffix 'summarizedActivities.json'\n" +
          "The plots will be saved in the script's directory.\n" +
          'Optional Arguments (for multiple values in the same field, use comma as a separator)')
    d = get_dict()
    all_act = [a + '_' + b for a in d.keys() for b in d[a].keys()]
    all_act_d = [i for i in all_act if '_d' in i]
    all_act_not_d = [i for i in all_act if '_d' not in i]

    print('\t--' + all_act_d[0] + (30 - len(all_act_d[0])) * ' ' + ' dates (DD/MM/YYYY) to draw vertical lines')
    print('\n'.join(['\t--' + i for i in all_act_d[1:]]))
    print(
        '\t--' + all_act_not_d[0] + (30 - len(all_act_not_d[0])) * ' ' + ' values (numerical) to draw horizontal lines')
    print('\n'.join(['\t--' + i for i in all_act_not_d[1:]]))


# parse users input for lines
def users_input():
    def validate_date(date_text):
        try:
            datetime.strptime(date_text, '%d-%m-%Y')
            return True
        except:
            print("Incorrect data format " + date_text.replace('-', '/') + ", should be DD-MM-YYYY" +
                  "\nTry 'python GarminZoomOut.py --help' for more information.")
            return False

    def validate_num(num_text):
        try:
            float(num_text)
            return True
        except:
            print("Incorrect input " + num_text + ", should be a number" +
                  "\nTry 'python GarminZoomOut.py --help' for more information.")
            return False

    # dict to hold inputs
    d = get_dict()
    all_act = [a + '_' + b for a in d.keys() for b in d[a].keys()]

    # loop over inputs (example format : "--lap_swimming_h=02/09/2016,03/12/2016")
    for k, v in ((k.lstrip('-'), v) for k, v in (a.split('=') for a in sys.argv[1:])):
        if k not in all_act:
            print('invalid option --' + k + "\nTry 'python GarminZoomOut.py --help' for more information.")
            continue
        act, variable = k.rsplit('_', 1)  # activity type, line direction
        if variable == 'd':
            v = v.replace('/', '-').split(',')  # dates list
            v = [d for d in v if validate_date(d)]  # check which ones are valid
        else:
            v = v.split(',')  # values list
            v = [i for i in v if validate_num(i)]
        if len(v):
            d[act] = {variable: v}
    return d


# get string of json file content and plot distribution of activities
def act_distribution(json_data):
    n_act = len(json_data)

    # list all activity types
    act_type_l = []
    for act in json_data:
        act_type_l.append(act['activityType'])

    # count activities frequency
    act_type_l = dict(Counter(act_type_l).most_common())
    # plot activities frequency
    plt.bar(act_type_l.keys(), act_type_l.values())
    plt.ylabel('Counts')
    plt.title('Activities distribution (N=' + str(n_act) + ')')
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig(out_dir + 'Activities_distribution.jpg')
    # plt.show()
    plt.close()
    # return list of activities with minimum entries
    return [n for n, v in act_type_l.items() if v > 20]


# act_type = ['lap_swimming'/ 'running'/ 'walking']
# get string of json file content and activity type to analyze
def act_analysis(data, act_type, lines):
    act_dist_scale = 1
    act_dist_cutoff = 1
    # adjust parameters according to activity type
    if act_type == 'lap_swimming':
        act_dist_scale = (1 / 100)  # cm to meter
        act_dist_cutoff = 100  # minimum 100 meters
    elif act_type in ['running', 'walking']:
        act_dist_scale = 1 / 100000  # cm to km
        act_dist_cutoff = 1  # minimum 1 km

    # collect all relevant activities from data
    act_list = []
    for act in data:
        # if this is the relevant activity and the distance passed a minimal cutoff
        if act['activityType'] == act_type and act['distance'] * act_dist_scale > act_dist_cutoff:
            act_list.append(act)

    # dict with the relevant metrics for the plots
    act_plot = {}
    for act in act_list:
        # timestamp in milliseconds to sec, and to datetime
        date_time = datetime.utcfromtimestamp(act['beginTimestamp'] / 1000)
        duration = act['duration'] * (1 / 60000)  # millisecond to minutes
        distance = act['distance'] * act_dist_scale  # convert to proper scale
        act_plot[date_time] = {'avgHr (bpm)': act['avgHr']}

        # add activity specific metrics
        if act_type == 'lap_swimming':
            avgLapTime = round(duration / distance * 100, 2)  # minutes/ 100 meter
            act_plot[date_time].update(
                {'avgLapTime (minutes/ 100 meter)': avgLapTime,
                 'avgStrokes (strokes/ 25 meter)': act['avgStrokes']})
        elif act_type == 'running':
            act_plot[date_time].update(
                {'Duration (minutes)': duration,
                 'avgPace (minutes/ km)': duration / distance,
                 'avgDoubleCadence (steps/ minute)': act['avgDoubleCadence']
                 }
            )
        elif act_type == 'walking':
            act_plot[date_time].update(
                {'Duration (minutes)': duration,
                 'Distance (km)': distance,
                 'avgPace (minutes/ km)': duration / distance,
                 }
            )

    # sort activities by date time
    act_plot = dict(sorted(act_plot.items()))

    act_df = pd.DataFrame(act_plot).T
    act_df.index = act_df.index.date  # index of date only (disregard time)
    # extract subplots titles list
    titles = act_df.columns.str.replace(' \((.*?)\)', '').to_list()
    # plot activity metrics over time
    axes = act_df.plot(subplots=True, legend=False, title=titles)
    plt.minorticks_off()  # turn off minor ticks
    # extract ylabels and set them in subplots
    ylabs = act_df.columns.str.extract('\((.*?)\)')[0].str.replace('/', "/\n").to_list()
    for i in range(len(axes)):
        axes[i].set_ylabel(ylabs[i])
        axes[i].text(0.8, 0.7, 'mean=' + str(round(act_df.iloc[:, i].mean(), 2)), size=10, transform=axes[i].transAxes)

    # add lines to empathize specific results, users input
    for k in lines.keys():
        # extract values in range
        if k == 'd':
            max_v = max(act_df.index)
            min_v = min(act_df.index)
            lines[k] = [datetime.strptime(i, '%d-%m-%Y').date() for i in lines[k]]
        else:
            colname = act_df.columns[act_df.columns.str.contains(k, )][0]
            max_v = act_df[colname].max()
            min_v = act_df[colname].min()
            lines[k] = [float(i) for i in lines[k]]
        lines[k] = [v for v in lines[k] if v <= max_v and v >= min_v]

        if len(lines[k]) and k == 'd':
            for v in lines[k]:
                for ax in plt.gcf().axes:
                    ax.axvline(x=v, color='black', linestyle='--')
        if len(lines[k]) and k != 'd':
            for v in lines[k]:
                ax = [ax for ax in plt.gcf().axes if ax.title._text == k][0]
                ax.axhline(y=v, color='black', linestyle='--')

    # add main title
    plt_name = act_type.capitalize().replace('_', ' ') + ' summary'
    plt.suptitle(plt_name)
    plt.tight_layout()
    plt.savefig(out_dir + plt_name + '.jpg')
    plt.close()

    # plot correlation of the different pairs in activity variables
    act_df['Month'] = act_df.index.astype(str).str[:-3].to_list()
    g = sns.pairplot(act_df, corner=True, hue='Month', palette='magma')
    plt_name = plt_name.replace(' summary', ' - variables correlation')
    g.fig.suptitle(plt_name)
    plt.savefig(out_dir + plt_name.replace(' -', '') + '.jpg')
    plt.close()


# main, read data, send to different functions
def main():
    # load activities json file
    f = open(file_path)
    json_data = json.load(f)
    f.close()

    json_data = json_data[0]['summarizedActivitiesExport']

    main_activities = act_distribution(json_data)  # overall view of activity types and freq

    lines_input = users_input()  # parse input, get dict

    # in depth analysis of specific activities types
    for act in ['lap_swimming', 'running', 'walking']:
        # if there are enough entries in this activity
        if act in main_activities:
            act_analysis(data=json_data, act_type=act, lines=lines_input[act].copy())


if len(sys.argv)>1 and sys.argv[1] == '--help':
    help_doc()
else:
    main()
