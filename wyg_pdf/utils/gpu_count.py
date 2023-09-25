# -*- encoding: utf-8 -*-
"""
@Time    : 2022/7/13 16:16
@Software: PyCharm
"""
import pynvml
from log import log


def get_gpu():
    UNIT = 1024 * 1024
    first_unused_gpu = None
    try:
        pynvml.nvmlInit()  # 初始化
    except Exception as e:
        log.logger.info("无显卡")
        return 0
    gpuDeriveInfo = pynvml.nvmlSystemGetDriverVersion()
    log.logger.info("Drive版本: {}".format(str(gpuDeriveInfo, encoding='utf-8')))  # 显示驱动信息

    gpuDeviceCount = pynvml.nvmlDeviceGetCount()  # 获取Nvidia GPU块数
    log.logger.info("GPU个数：{}".format(int(gpuDeviceCount)))
    try:
        for i in range(gpuDeviceCount):
            handle = pynvml.nvmlDeviceGetHandleByIndex(i)  # 获取GPU i的handle，后续通过handle来处理
            memoryInfo = pynvml.nvmlDeviceGetMemoryInfo(handle)  # 通过handle获取GPU i的信息
            gpuName = str(pynvml.nvmlDeviceGetName(handle), encoding='utf-8')
            gpuTemperature = pynvml.nvmlDeviceGetTemperature(handle, 0)
            gpuFanSpeed = pynvml.nvmlDeviceGetFanSpeed(handle)
            gpuPowerState = pynvml.nvmlDeviceGetPowerState(handle)
            gpuUtilRate = pynvml.nvmlDeviceGetUtilizationRates(handle).gpu
            gpuMemoryRate = pynvml.nvmlDeviceGetUtilizationRates(handle).memory
            log.logger.info("第 {} 张卡：{}".format(i, "-" * 30))
            log.logger.info("显卡名：{}".format(gpuName))
            log.logger.info("显存总容量：{} MB".format(memoryInfo.total / UNIT))
            log.logger.info("使用容量：{} MB".format(memoryInfo.used / UNIT))
            log.logger.info("剩余容量：{} MB".format(memoryInfo.free / UNIT))
            log.logger.info("显存空闲率：{}".format(memoryInfo.free / memoryInfo.total))
            log.logger.info("温度：{}摄氏度".format(gpuTemperature))
            log.logger.info("风扇速率：{}".format(gpuFanSpeed))
            log.logger.info("供电水平：{}".format(gpuPowerState))
            log.logger.info("gpu计算核心满速使用率：{}".format(gpuUtilRate))
            log.logger.info("gpu内存读写满速使用率：{}".format(gpuMemoryRate))
            log.logger.info("内存占用率：{}".format(memoryInfo.used / memoryInfo.total))
            """
            # 设置显卡工作模式
            # 设置完显卡驱动模式后，需要重启才能生效
            # 0 为 WDDM模式，1为TCC 模式
            gpuMode = 0     # WDDM
            gpuMode = 1     # TCC
            pynvml.nvmlDeviceSetDriverModel(handle, gpuMode)
            # 很多显卡不支持设置模式，会报错
            # pynvml.nvml.NVMLError_NotSupported: Not Supported
            """
            # 对pid的gpu消耗进行统计
            pidAllInfo = pynvml.nvmlDeviceGetComputeRunningProcesses(handle)  # 获取所有GPU上正在运行的进程信息
            for pidInfo in pidAllInfo:
                log.logger.info("进程pid：{}, 显存占有：{} MB".format(pidInfo.pid,
                                pidInfo.usedGpuMemory / UNIT))  # 统计某pid使用的显存

            if memoryInfo.free / UNIT > 0.9 * memoryInfo.total / UNIT and first_unused_gpu is None:
                first_unused_gpu = i
    except:
        pass
    pynvml.nvmlShutdown()  # 最后关闭管理工具
    if first_unused_gpu is None:
        log.logger.error("未找到未使用的显卡，请检查")
    return first_unused_gpu
