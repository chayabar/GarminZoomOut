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


# return dictionary with parameters structure for each activity type
def act_parameters_dict():
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
    act_param_d = act_parameters_dict()
    # make a list of all activities with their specific parameters
    all_act_param = []
    for act_name in act_param_d.keys():
        act_param = act_param_d[act_name].keys()
        all_act_param += [act_name + '_' + param for param in act_param]
    all_act_d = [i for i in all_act_param if '_d' in i]
    all_act_not_d = [i for i in all_act_param if '_d' not in i]

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
            print("Incorrect date format " + date_text.replace('-', '/') + ", should be DD-MM-YYYY" +
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
    act_param_d = act_parameters_dict()
    # make a list of all activities with their specific parameters
    all_act_param = []
    for act_name in act_param_d.keys():
        act_param = act_param_d[act_name].keys()
        all_act_param += [act_name + '_' + param for param in act_param]

    # loop over inputs (example format : "--lap_swimming_h=02/09/2016,03/12/2016")
    input_pairs = [input.lstrip('-').split('=') for input in sys.argv[1:]]
    for field, val in input_pairs:
        if field not in all_act_param:
            print('invalid option --' + field + "\nTry 'python GarminZoomOut.py --help' for more information.")
            continue
        act, param = field.rsplit('_', 1)  # activity type, line direction
        if param == 'd':
            val = val.replace('/', '-').split(',')  # dates list
            val = [date for date in val if validate_date(date)]  # check which ones are valid
        else:
            val = val.split(',')  # values list
            val = [num for num in val if validate_num(num)]
        if len(val):
            act_param_d[act] = {param: val}
    return act_param_d


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
    return [act_n for act_n, count in act_type_l.items() if count > 20]


# get activity type, return distance scale and minimal cutoff
def act_dist(act_type):
    act_dist_scale = 1
    act_dist_cutoff = 1
    # adjust parameters according to activity type
    if act_type == 'lap_swimming':
        act_dist_scale = (1 / 100)  # cm to meter
        act_dist_cutoff = 100  # minimum 100 meters
    elif act_type in ['running', 'walking']:
        act_dist_scale = 1 / 100000  # cm to km
        act_dist_cutoff = 1  # minimum 1 km
    return act_dist_scale, act_dist_cutoff


# get activity type name and list with activities from this type
# return df with relevant metrics for this activity
def extract_act_features(act_type, act_list):
    act_dist_scale = act_dist(act_type)[0]
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
    return act_plot


# get activity df, lines dict and axes. check which lines in df range, add to plot
def add_lines(act_df, lines, axes):
    for metric in lines.keys():
        # extract values in range
        if metric == 'd':
            max_metric = max(act_df.index)
            min_metric = min(act_df.index)
            # convert metric to date format
            lines[metric] = [datetime.strptime(i, '%d-%m-%Y') for i in lines[metric]]
        else:
            colname = act_df.columns[act_df.columns.str.contains(metric, )][0]
            max_metric = act_df[colname].max()
            min_metric = act_df[colname].min()
            lines[metric] = [float(i) for i in lines[metric]]
        # filter all values that in data metric range
        lines[metric] = [val for val in lines[metric] if val <= max_metric and val >= min_metric]

    # add lines to empathize specific results, users input
    for metric in lines.keys():
        # add vertical date lines
        if len(lines[metric]) and metric == 'd':
            for val in lines[metric]:
                for ax in axes:
                    ax.axvline(x=val, color='black', linestyle='--')
        # add horizontal metric lines
        if len(lines[metric]) and metric != 'd':
            for val in lines[metric]:
                ax = [ax for ax in axes if ax.title._text == metric][0]
                ax.axhline(y=val, color='black', linestyle='--')


# get activity df, dict for plot lines, act type. save plots to out dir
def act_plot(act_df, act_type, lines):
    # extract subplots titles list
    titles = act_df.columns.str.replace(' \((.*?)\)', '', regex=True).to_list()
    # plot activity metrics over time
    axes = act_df.plot(subplots=True, legend=False, title=titles)
    plt.minorticks_off()  # turn off minor ticks
    # extract ylabels and set them in subplots
    ylabs = act_df.columns.str.extract('\((.*?)\)')[0].str.replace('/', "/\n").to_list()
    # set ylabels and add mean text
    for i in range(len(axes)):
        axes[i].set_ylabel(ylabs[i])
        axes[i].text(0.8, 0.7, 'mean=' + str(round(act_df.iloc[:, i].mean(), 2)), size=10, transform=axes[i].transAxes)

    add_lines(act_df, lines, axes)

    # add main title
    plt_name = act_type.capitalize().replace('_', ' ') + ' summary'
    plt.suptitle(plt_name)
    plt.tight_layout()
    plt.savefig(out_dir + plt_name + '.jpg')
    plt.close()

    # plot correlation of the different pairs in activity variables
    act_df['Month'] = pd.Series(act_df.index.date).astype(str).str[:-3].to_list()
    g = sns.pairplot(act_df, corner=True, hue='Month', palette='magma')
    plt_name = plt_name.replace(' summary', ' - variables correlation')
    g.fig.suptitle(plt_name)
    plt.savefig(out_dir + plt_name.replace(' -', '') + '.jpg')
    plt.close()


# act_type = ['lap_swimming'/ 'running'/ 'walking']
# get string of json file content and activity type to analyze
def act_analysis(data, act_type, lines):
    act_dist_scale, act_dist_cutoff = act_dist(act_type)
    # collect all relevant activities from data
    act_list = []
    for act in data:
        # if this is the relevant activity and the distance passed a minimal cutoff
        if act['activityType'] == act_type and act['distance'] * act_dist_scale > act_dist_cutoff:
            act_list.append(act)

    act_df = extract_act_features(act_type, act_list)
    act_df = pd.DataFrame(act_df).T
    act_plot(act_df, act_type, lines)


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
