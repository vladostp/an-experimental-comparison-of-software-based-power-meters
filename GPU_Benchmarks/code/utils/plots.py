"""Plot functions for timeseries visualisations."""

import itertools
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
import numpy as np
import re

LINESTYLES = [
    (0,(1, 1)),
    (0, (2, 2)),
    (0, (3, 3)),
    (0, (4, 4)),
    (0, (3, 1, 1, 1)),
    (0, (4, 1, 1, 1)),
    (0, (5, 1, 1, 1)),
    (0, (6, 1, 2, 1)),
    (0, (3, 1)),
    (0, (4, 1)),
    (0, (5, 1)),
    ]
FIGSIZE = (15,10)
FONTSIZE = 20
COLOR = plt.cm.tab20

def create_line_legend(cols, LINESTYLES):
    linestyle_iter = itertools.cycle(LINESTYLES)
    lines = []
    for _ in cols:
        line = next(linestyle_iter)
        lines.append(Line2D([0], [0],
                            color='black',
                            linestyle=line,
                            linewidth=4,
                           ))
    return lines

def create_color_legend(bench_ids, COLOR):
    if isinstance(COLOR, list):
        color = itertools.cycle(COLOR)
    else:
        color = itertools.cycle(COLOR(np.linspace(0, 1, len(bench_ids)+1)))
    lines = []
    for _ in bench_ids:
        c = next(color)
        lines.append(Line2D([0], [0],
                            color=c,
                            linewidth=4,
                           ))
    return lines
    
def process_bench_legend(bench_ids):
    return ["Experiment ID: "+ bid for bid in bench_ids]

def process_col_name(col_name):
    """Process the columns of the DataFrame so that they can be understood by reader.
    
    ''data.arch.chifflet-6.arch.gpu-nvidia-0.data.ecpu(W)''
    format = data.arch.<node>.arch.<component>.data.<processeur or memory>
    
    List of timeseries:
    ['timestamp', 'wattmetre_power_watt', 'timestamp_sec',
       'bmc_node_power_watt', 'pdu_outlet_power_watt', 'data.data.etotal(W)',
       'data.data.ecpu(W)', 'data.data.edram(W)',
       'arch.0.data.ecpu(W)',
       'arch.0.data.edram(W)',
       'arch.1.data.ecpu(W)',
       'arch.1.data.edram(W)',
       'arch.gpu-nvidia-0.data.ecpu(W)',
       'arch.gpu-nvidia-0.data.edram(W)',
       'arch.gpu-nvidia-1.data.ecpu(W)',
       'arch.gpu-nvidia-1.data.edram(W)', 'sec']

    args
        col_name: str of format described above

    returns
        component: str of component number. For example '0' or 'gpu-nvidia-1' 
        type: str. should be 'processeur' or 'dram'
    """
    if "power_watt" in col_name:
        if "wattmetre" in col_name:
            return "External power meter"
        elif "bmc" in col_name:
            return "BMC"
        else:
            split_list = col_name.split('_')
            return split_list[0].capitalize()

    elif col_name=="wattmetre_es_diff":
        return "Offset \n(Wattmetre - Energy Scope)"
        
    elif "data.data" in col_name:
        label = "Total " + re.search(r'data.data.e(.*?)\(W\)', col_name).group(1)
        if label == "Total total":
            return "Energy Scope"
        return label
        
    elif "arch" in col_name:
        split_list = col_name.split('.')
        arch, type = split_list[1], split_list[3]

        if 'gpu' in arch:
            component = 'gpu'
            number = arch.split('-')[-1]
        else:
            component = 'cpu'
            number = arch

        if type == 'ecpu(W)':
            type = ''
        else:
            type = 'dram '

        return '{}{} {}'.format(type, component, number).upper()
    else:
        return col_name.capitalize()

def process_col_legend(cols):
    return [process_col_name(col) for col in cols]

def plot_all_experiments_of_one_bench(
    df, 
    bench_ids, 
    cols, 
    _,
    ax, 
    FONTSIZE, 
    legend_fontsize,
    LINESTYLES, 
    COLOR, 
    appli, 
    appli_class, 
    if_col_legend, 
    if_bench_legend, 
    bbox_to_anchor,
    loc,
    ncol_legend,
    plot_limits,
    ):
    """Plots the graphs of timeseries for given experiment ids.

    args:
        df: DataFrame. Timeseries of experiments.
        bench_ids: List of strings. Ids of the experiments to include in the statistics.
        cols: list of strings. List of columns to plot.
        ax: matplotlib axe.
        FONTSIZE: int. Fontsize to use for the plot.
        styles: List of strings. Linestyles to use for the plot.
        COLOR: Matplotlib color map.
        appli: String. Benchmark application (For labels)
        appli_class: String. Benchmark application class (For labels)
        if_col_legend: Bool.
            By default True 
        if_bench_legend: Bool
            By default True
        plot_limits: Tuple. (minumum, maximum)
            By default None
    """
    linestyle_iter = itertools.cycle(LINESTYLES)

    for b_id in bench_ids:
        line = next(linestyle_iter)
        if isinstance(COLOR, list):
            color = itertools.cycle(COLOR)
        else:
            color = itertools.cycle(COLOR(np.linspace(0, 1, len(cols)+1)))

        ymin=df[cols].min(0).min()
        ymax=df[cols].max(0).max()
        ax.vlines(df[df['benchmark_id']==b_id]['sec'].min() + 30, ymin=ymin, ymax=ymax, color='black', linestyles=line) # 
        ax.vlines(df[df['benchmark_id']==b_id]['sec'].max() - 30 , ymin=ymin, ymax=ymax, color='black', linestyles=line) # 
        
        for col in cols:
            c=next(color)
            c = c if isinstance(c, str) else c.reshape(-1,4)
            droped_df = df[df['benchmark_id']==b_id].dropna(subset=['sec', col])
            if not droped_df.empty:
                droped_df.plot(
                    ax=ax, 
                    x='sec', 
                    y=col,
                    color=c,
                    linestyle=line,
                    linewidth=2.5,
                    fontsize=FONTSIZE,
                )
    bench_legend_style = create_line_legend(bench_ids, LINESTYLES)
    col_legend_style = create_color_legend(cols, COLOR)

    if if_col_legend and if_bench_legend:
        legend_lines = col_legend_style+bench_legend_style
        legend_labels = process_col_legend(cols)+process_bench_legend(bench_ids)
    elif if_bench_legend and not if_col_legend:
        legend_lines = bench_legend_style
        legend_labels = process_bench_legend(bench_ids)
    elif not if_bench_legend and if_col_legend:
        legend_lines = col_legend_style
        legend_labels = process_col_legend(cols)
    
    ax.legend(
        legend_lines, 
        legend_labels, 
        bbox_to_anchor=(1, 1), 
        fontsize=FONTSIZE-40,
    )

    if not if_bench_legend and not if_col_legend:
        ax.get_legend().remove()
        
    ax.set_xlabel('Timestamps (S)', fontsize=FONTSIZE)
    ax.set_ylabel('Power (W)', fontsize=FONTSIZE)
    ax.set_title('Evolution of the power with NAS benchmark application {} class {}.'.format(appli, appli_class),
                 y=-0.12, 
                 fontsize=FONTSIZE+5
                )
    if plot_limits is not None:
        ax.set_ylim(plot_limits)
    return ax, legend_labels

def plot_quantiles_of_one_bench(
    df, 
    bench_ids, 
    cols, 
    stat_cols,
    ax, 
    FONTSIZE, 
    legend_fontsize,
    styles, 
    COLOR, 
    appli, 
    appli_class, 
    if_col_legend, 
    if_bench_legend, 
    bbox_to_anchor,
    loc,
    ncol_legend,
    plot_limits,
    ):
    """Plots the graphs of given statistics for given experiment ids.

    This means data is replicated to fill missing data and statistics might
    not be exact.

    args:
        df: DataFrame. Timeseries of experiments.
        bench_ids: List of strings. Ids of the experiments to include in the statistics.
        cols: list of strings. List of columns to plot.
        stat_cols: List of statistics to plot.
        ax: matplotlib axe.
        FONTSIZE: int. Fontsize to use for the plot.
        styles: List of strings. Linestyles to use for the plot.
        COLOR: Matplotlib color map.
        appli: String. Benchmark application (For labels)
        appli_class: String. Benchmark application class (For labels)
        if_col_legend: Bool.
            By default True 
        if_bench_legend: Bool
            By default True
        plot_limits: Tuple. (minumum, maximum)
            By default None
    """
    if isinstance(COLOR, list):
        color = itertools.cycle(COLOR)
    else:
        color = itertools.cycle(COLOR(np.linspace(0, 1, len(cols)+1)))
    ymin, ymax = np.inf, 0
    for col in cols:
        c = next(color)
        test_df = df[df['benchmark_id'].isin(bench_ids)][
            ['sec', col]].groupby(
            by=['sec']).describe(percentiles = [0.05, 0.1, 0.25, 0.5, 0.75, 0.9, 0.95])
        test_df[col].plot(
            y=stat_cols, 
            color=c, 
            style=styles,
            ax=ax,
            fontsize=FONTSIZE-7,
            )
        ax.fill_between(
            test_df.index.values, 
            test_df[col][stat_cols[0]].values,
            test_df[col][stat_cols[-1]].values, 
            alpha=0.3, 
            color=c,
            )

        ymin = test_df[col][stat_cols].min(0).min() if test_df[col][stat_cols].min(0).min() < ymin else ymin
        ymax = test_df[col][stat_cols].max(0).max() if test_df[col][stat_cols].max(0).max() > ymax else ymax

    if plot_limits is not None:
        ymin, ymax = plot_limits
        ax.set_ylim(plot_limits)

    lines = create_line_legend(stat_cols, styles)
    legend_color = create_color_legend(cols, COLOR)

    if if_col_legend and if_bench_legend:
        legend_lines = legend_color+lines
        legend_labels = process_col_legend(cols)+stat_cols[::-1]
    elif if_bench_legend and not if_col_legend:
        legend_lines = lines
        legend_labels = stat_cols[::-1]
    elif not if_bench_legend and if_col_legend:
        legend_lines = legend_color
        legend_labels = process_col_legend(cols)
    else:
        legend_lines=[]
        legend_labels=[]
        
    ax.legend(
        legend_lines, 
        legend_labels, 
        bbox_to_anchor=bbox_to_anchor, 
        loc=loc,
        fontsize=legend_fontsize,
        ncol=ncol_legend,
    )

    if not if_bench_legend and not if_col_legend:
        ax.get_legend().remove()

    ax.set_xlabel('Time (S)', fontsize=FONTSIZE)
    ax.set_ylabel('Power (W)', fontsize=FONTSIZE)
    ax.set_title('{} NAS Benchmark'.format(appli.upper()),
            fontsize=FONTSIZE,
        )

    return ax, legend_labels
    
def plot_subplot_per_appli_per_class(
    exp_table, 
    df, 
    cols, 
    FONTSIZE, 
    LINESTYLES, 
    COLOR, 
    legend_fontsize=None,
    FIGSIZE=None,
    bench_plot_fct=plot_all_experiments_of_one_bench, 
    stat_cols = None,
    plot_limits=None, 
    if_col_legend=True, 
    if_bench_legend=True,
    bbox_to_anchor=(0,1),
    loc='upper left',
    nb_cols=1,
    ncol_legend=1,
    ):
    """Creates the matplotlib figure and plots the graphs for every benchmark in the dataframe.

    args:
        exp_table: DataFrame. Description of the experiments
        df: DataFrame. Timeseries of experiments.
        cols: list of strings. List of columns to plot.
        FONTSIZE: int. Fontsize to use for the plot.
        LINESTYLES: List. Linestyles to use for the plot.
            Should match the number of experiments if the bench_plot_fct is plot_all_experiments_of_one_bench.
            For example:
            LINESTYLES = [
                (0,(1, 1)),
                (0, (2, 2))
                ]
        COLOR: Matplotlib color map.
        bench_plot_fct: fct to use for the plot.
            By default plot_all_experiments_of_one_bench 
        stat_cols: List of statistics to plot if bench_plot_fct is plot_quantiles_of_one_bench.
            By default None
        plot_limits: Tuple. (minumum, maximum)
            By default None
        if_col_legend: Bool.
            By default True 
        if_bench_legend: Bool
            By default True
        bbox_to_anchor
        loc
        nb_cols: Number of column in the subplot.
            By default 1
    """
    if legend_fontsize==None:
        legend_fontsize = FONTSIZE
    idx = exp_table.set_index(['gpu_0_appli','gpu_0_appli_class']).index.unique()
    exp_number = len(idx)
    if exp_number%nb_cols:
        nb_rows = exp_number//nb_cols+1
    else:
        nb_rows = exp_number//nb_cols

    FIGSIZE = (20*nb_cols,nb_rows*12) if FIGSIZE is None else FIGSIZE
    fig, axes = plt.subplots(
        nrows=nb_rows, 
        ncols=nb_cols, 
        sharex=False, 
        sharey=True, 
        figsize=FIGSIZE,
    )
    if nb_cols==1:
        axes=[[ax] for ax in axes]
    if nb_rows==1:
        axes=[axes]
    for i in range(exp_number):
        appli = idx[i][0]
        appli_class = idx[i][1]
        bench_ids = exp_table[(
            exp_table['gpu_0_appli']==appli)&(
            exp_table['gpu_0_appli_class']==appli_class)&(
            exp_table['tool_name']=='energy scope'
        )]['gpu_0_benchmark_id'].values
        axes[i//nb_cols][i%nb_cols], legend_labels = bench_plot_fct(
            df, 
            bench_ids, 
            cols, 
            stat_cols, 
            axes[i//nb_cols][i%nb_cols], 
            FONTSIZE, 
            legend_fontsize,
            LINESTYLES, 
            COLOR, 
            appli, 
            appli_class, 
            if_col_legend, 
            if_bench_legend, 
            bbox_to_anchor,
            loc,
            ncol_legend,
            plot_limits,
            )
    fig.tight_layout()
    return fig, axes, legend_labels