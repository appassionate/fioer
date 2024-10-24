import pandas as pd

import numpy as np
import json
import matplotlib.pyplot as plt

_DPI = 600
LATENCY_TYPE = ("slat", "clat", "lat")


def cumsum(array):
    return np.cumsum(array) / np.arange(1, len(array) + 1)

def _load_json(file):
    
    with open(file, "r") as f:
        data = json.load(f)
    return data

def _create_fig():
    return plt.subplots(figsize=(10, 3), dpi=_DPI)

class FioView():
    
    def __init__(self, job):
        
        self._job = job
        self.output_file = self._job.get_file_directory("parsed.json")

    def view_latency(self, mode="write", lat_type="", job_num=0, ax=None):
        
        output = _load_json(self.output_file)
        
        if lat_type not in LATENCY_TYPE:
            raise ValueError(f"latency type not supported: {lat_type}")
        
        lenframe = len(output)
        collect_lat_ns_mean = [ _frame["jobs"][job_num][mode][f"{lat_type}_ns"]["mean"] for _frame in output]
        collect_cum_lat_ns_mean = cumsum(collect_lat_ns_mean)
        # ns trans to μs array
        collect_lat_mean = np.array(collect_lat_ns_mean) / 1000
        collect_cum_lat_mean = np.array(collect_cum_lat_ns_mean) / 1000
        
        
        #fig, ax
        if not ax:
            fig, ax = plt.subplots(figsize=(10, 3),dpi=_DPI)
        else:
            fig = ax.get_figure()
        
        # 绘制折线图
        ax.plot(range(len(output)), collect_lat_mean, label=f"{lat_type}_mean", color="b")
        ax.plot(range(len(output)), collect_cum_lat_mean, label=f"{lat_type}_mean_cum", color="r")
        
        # 添加标题和标签
        ax.set_title(f"{mode.upper()}: Latency: {lat_type.upper()} Over {lenframe} Frames")
        ax.set_xlabel("Time (Frame)")
        ax.set_ylabel("Latency (μs)")
        
        # 显示网格和图例
        ax.grid(True)
        ax.legend()
        
        
        #grid setting: "--"
        ax.grid(True, linestyle='--')
        
        plt.show()
        
        return fig, ax

    def view_iops(self, mode, job_num=0, ax=None):
        
        output = _load_json(self.output_file)
        lenframe = len(output)
        
        collect_iops_mean = [frame["jobs"][0][mode]["iops"] for frame in output]
        collect_iops      = [frame["jobs"][0][mode]["iops_mean"] for frame in output]


        # traj[0]["jobs"][0]["write"]["iops_min"]
        # traj[0]["jobs"][0]["write"]["iops_max"]

        # traj[0]["jobs"][0]["write"]["iops_stddev"]
        #traj[0]["jobs"][0]["write"]["iops_samples"]

        #fig, ax
        if not ax:
            fig, ax = plt.subplots(figsize=(10, 3),dpi=_DPI)
        else:
            fig = ax.get_figure()

        # 绘制折线图
        ax.plot(range(len(output)), collect_iops_mean, label="iops_mean", color="b")
        ax.plot(range(len(output)), collect_iops     , label="iops", color="r")

        # 添加标题和标签
        ax.set_title(f"{mode.upper()}: IOPS Over {lenframe} Frames")
        ax.set_xlabel("Time (s)")
        ax.set_ylabel("IOPS")

        # 显示网格和图例
        ax.grid(True)
        ax.legend()

        # ax.set_xlim(0,100)
        # ax.set_ylim(0,1000000)

        #grid setting: "--"
        ax.grid(True, linestyle='--')

        # 显示图像
        plt.show()
        return fig, ax


    def overview_latency(self, mode="write", lat_type="lat"):
        
        # 总图,包含job_num个子图, n行1列
        output = _load_json(self.output_file)
        job_num = len(output[0]["jobs"])
        print(job_num)
        fig, axs = plt.subplots(job_num, 1, figsize=(10, 3 * job_num), dpi=_DPI)
        
        #avoiding subscriptable error
        if job_num == 1:
            axs = [axs]

        for i in range(job_num):
            self.view_latency(mode=mode, lat_type=lat_type, job_num=i, ax=axs[i])
        plt.show()
            
