import ctypes
from ctypes import POINTER, c_void_p, c_ushort, c_char, c_long, c_bool, c_int
import cgitb
import logging
import cv2
import os
import numpy as np
from enum import Enum

print(cv2.__version__)



# DLL路径输入
# dll_path = input("请输入P_XYZ_DI.dll的路径: ")
dll_path = r"D:\博士研究生\实验\RGB-D教程\RGB-D\P_XYZ_DI.dll"

# 加载DLL
p_xyz_di = ctypes.WinDLL(dll_path)


#####################################################第一部分涉及到的全局信息###############################################

# 定义C++中的结构体 设备选择信息 P_XYZ_Common.h
class DEVSELINFO(ctypes.Structure):
    _fields_ = [("index", c_long)]


# 定义C++中的结构体和函数原型 对应 P_XYZ_Common.h 中 DEVINFORMATIONEX
class DEVINFORMATIONEX(ctypes.Structure):
    _fields_ = [
        ("wPID", c_ushort),
        ("wVID", c_ushort),
        ("strDevName", c_char * 512),  # 512个字符的数组
        ("nChpID", c_ushort),
        ("nDevType", c_ushort)
    ]


# 定义C++中的结构体 对应 P_XYZ_Common.h 中 LenaDDI_STREAM_INFO
class LenaDDI_STREAM_INFO(ctypes.Structure):
    _fields_ = [
        ("nWidth", c_int),
        ("nHeight", c_int),
        ("bFormatMJPG", c_int),  # 假设BOOL在C中实现为int
    ]


# 定义C++中的结构体 对应 P_XYZ_Common.h 中 SENSOR_TYPE_NAME
class SENSOR_TYPE_NAME(Enum):
    H65 = 0
    H65_TEMP = 1
    AR0135_TEMP = 2
    AR0135 = 3


# 全局变量  对应c++在device_Ini.h中用到的，也是在 python 执行DeviceInit()方法中用到的
XYZ_Cam = c_void_p()  # 指向相机设备的指针 对应 device_Ini.h 中 void* XYZ_Cam;
XYZ_Cam_Index = 0  # 相机设备编号 对应 device_Ini.h 中 int XYZ_Cam_Index = 0;
XYZ_Cam_Info = DEVSELINFO()  # 设备选择信息 对应 device_Ini.h 中 DEVSELINFO XYZ_Cam_Info;
XYZ_Cam_Color_Resolution = (
        LenaDDI_STREAM_INFO * 64)()  # 视频流分辨率信息 对应 device_Ini.h 中 LenaDDI_STREAM_INFO XYZ_Cam_Color_Resolution[LenaDDI_MAX_STREAM_COUNT];
XYZ_Cam_Depth_Resolution = (
        LenaDDI_STREAM_INFO * 64)()  # 视频流分辨率信息 对应 device_Ini.h 中 LenaDDI_STREAM_INFO XYZ_Cam_Color_Resolution[LenaDDI_MAX_STREAM_COUNT];
usb3_0 = False  # 对应 device_Ini.h 中 bool usb3_0 = false;
m_depthType = 4  # 对应 device_Ini.h 中 int m_depthType; 不同之处在于，python直接给m_depthType赋值了 在c++中 由Depth_Data_Type和XYZ_Cam_Rectify_Option共同决定
XYZ_Cam_Color_Option = 0  # 对应 main.cpp 中 XYZ_Cam_Color_Option; 作用是选择原图的图像分辨率,0：左目1280x720 ； 1:左目1280x720 + 右目1280x720
Camera_Model = 0  # 对应 main.cpp 中int Camera_Model = 0; 自动识别出来的相机曝光芯片型号
XYZ_Cam_Rectify_Option = 0  # 对应 main.cpp 中int XYZ_Cam_Rectify_Option = 0;为0表示输出校正后的原图数据，为1表示输出未校正的原图数据。
Depth_Data_Type = 0  # 对应 main.cpp 中 int Depth_Data_Type = 0; USB3.0接口下，输出11bit深度图，也就是单位为像素的视差图

# 回调函数 callback_fn 和 彩色图像、深度图像处理过程中用到的
color_img = None  # python 中变量类型是动态的，这里可以对应 main.cpp 中 Mat ColorRawData; 用于存放原图的数据
depth_img = None  # python 中变量类型是动态的，这里可以对应 main.cpp 中 Mat DepthRawData; 用于存放相机输出的原始视差数据，并根据它计算每个像素点的xyz三维坐标
color_new_flag = False  # 对应 main.cpp 中 uchar ColorNewFlag = 0; 标志位，True表示采集到一帧新的原图
depth_new_flag = False  # 对应 main.cpp 中 uchar DepthNewFlag = 0; 标志位，True表示采集到一帧新的深度图
color_img_resized = None  # python 中变量类型是动态的，这里可以对应 main.cpp 中 Mat ColorRawData_ReSize; 用于存放缩放后的原图
depth_img_resized = None  # python 中变量类型是动态的，这里可以对应 main.cpp 中 Mat DepthDisplay_ReSiz; 用于存放彩色仅供观察用的深度图
depth_img_in = None  # python 中变量类型是动态的，这里可以对应 main.cpp 中 Mat DepthRawData; 用于存放相机输出的原始视差数据，并根据它计算每个像素点的xyz三维坐标
# 图像处理的全局变量
cross_x, cross_y = 320, 180  # 0.5缩放图像的初始交叉位置 对应 main.cpp 中 uint cross_x = 320; uint cross_y = 180;
num = 1  # 图像保存计数器 对应 main.cpp 中 int num = 1;

# 配置参数(应根据您的摄像头设置进行设置)
ccpoint_LX, ccpoint_LY = 642, 361  # 校准点 对应 main.cpp 中 ccpoint_LX = 658; uint ccpoint_LY = 359;
Focus_Pixel = 1200  # 焦距(像素)
BaseLine = 179.721 # 基线(毫米)

resize_dims = (640, 360)
resize_dims2 = (1280, 360)

Pos_x = 0
Pos_y = 0
Pos_z = 0
RGB_R = 0
RGB_G = 0
RGB_B = 0

Mouse_Point = (0, 0)  # 鼠标按下的起始点
Mouse_selectObject = False  # 是否选择对象
Mouse_selection = [0, 0, 0, 0]  # 定义矩形选框


######################################################第二部分关于设备初始化################################################

# 对应 LenaDDIUtility.cpp 中 CLenaDDIWrap::CLenaDDIWrap() : hLenaDDI(NULL
class CLenaDDIWrap(object):
    def __init__(self):
        self.hLenaDDI = c_void_p()
        result = p_xyz_di.LenaDDI_Init(ctypes.byref(self.hLenaDDI), False)
        logging.info(f"初始化结果: {result}")
        if result < 0:
            raise Exception("LenaDDI_Init失败")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.release()

    def release(self):
        if self.hLenaDDI:
            p_xyz_di.LenaDDI_Release(ctypes.byref(self.hLenaDDI))
            self.hLenaDDI = None


# 对应 LenaDDIUtility.cpp 中 bool GetLenaDDIDevice(std::vector<DEVINFORMATIONEX>& device) 返回的devices是bytes对象
# 在python中使用前需要解码bytes对象
def get_lena_ddi_devices():
    logging.info("开始获取Lena DDI设备")
    devices = []
    with CLenaDDIWrap() as wrap:
        count = p_xyz_di.LenaDDI_GetDeviceNumber(wrap.hLenaDDI)
        logging.info(f"设备数量: {count}")
        for i in range(count):
            dev_sel = DEVSELINFO(i)
            dev_info = DEVINFORMATIONEX()
            ret = p_xyz_di.LenaDDI_GetDeviceInfoEx(wrap.hLenaDDI, ctypes.byref(dev_sel), ctypes.byref(dev_info))
            if ret == 0:
                devices.append(dev_info)
            else:
                logging.info(f"获取设备信息失败，错误代码: {ret}")
                break
    return devices


# 对应 device_Ini.h 中 int DeviceInit(void) 功能是设备初始化
def DeviceInit():
    # 使用全局变量
    global XYZ_Cam, XYZ_Cam_Index, XYZ_Cam_Info, Camera_Model
    global XYZ_Cam_Color_Resolution, XYZ_Cam_Depth_Resolution, usb3_0, m_depthType

    # 定义参数 在LenaDDI_OpenDeviceEx使用
    to_rgb = True
    depth_stream_index = 0
    depth_stream_switch = 2
    callback_param = None

    ############
    # 初始化设备 #
    ############
    init2 = p_xyz_di.LenaDDI_Init2(ctypes.byref(XYZ_Cam), False, True)
    print(f"init2:{init2}")

    # 获取设备信息
    devices_init = get_lena_ddi_devices()

    for dev in devices_init:
        if dev.strDevName == "XYZ 3d:vid_0211 pid_5838" or dev.strDevName == "PixelXYZ 3d Cam:vid_0211 pid_5838":
            XYZ_Cam_Index = dev.index
            if dev.strDevName == "XYZ 3d:vid_0211 pid_5838":
                Camera_Model = 0
            else:
                Camera_Model = 1
            break

    XYZ_Cam_Info.index = XYZ_Cam_Index
    print(f"XYZ_Cam_Info.index:{XYZ_Cam_Info.index}")

    # 获取分辨率
    GetDeviceResolutionList = p_xyz_di.LenaDDI_GetDeviceResolutionList(XYZ_Cam, ctypes.byref(XYZ_Cam_Info), 64,
                                                                       XYZ_Cam_Color_Resolution, 64,
                                                                       XYZ_Cam_Depth_Resolution)
    print(f"GetDeviceResolutionList:{GetDeviceResolutionList}")

    if XYZ_Cam_Depth_Resolution[0].nWidth == 1280:
        usb3_0 = True

    # 设置数据格式
    if usb3_0:
        if Depth_Data_Type == 0:
            if XYZ_Cam_Rectify_Option == 0:
                m_depthType = 4
            else:
                m_depthType = 9

    SetDepthDataType_state = p_xyz_di.LenaDDI_SetDepthDataType(XYZ_Cam, ctypes.byref(XYZ_Cam_Info),
                                                               ctypes.c_int(m_depthType))
    print(f"SetDepthDataType_state:{SetDepthDataType_state}")

    if SetDepthDataType_state != 0:
        print("Output Depth Data Failed ..")
        return 1
    else:
        print("Output Depth Data succeeded")

    # fps作为ctypes对象
    fps = ctypes.c_int(30)

    # 调用LenaDDI_OpenDeviceEx
    ret = p_xyz_di.LenaDDI_OpenDeviceEx(
        XYZ_Cam,
        ctypes.byref(XYZ_Cam_Info),
        ctypes.c_int(XYZ_Cam_Color_Option),
        to_rgb,
        depth_stream_index,
        depth_stream_switch,
        callback_fn,  # 直接传递回调函数
        callback_param,
        ctypes.byref(fps),
        ctypes.c_int(0)
    )
    print(f"ret:{ret}")

    # 打印修改后的fps
    print(fps.value)

    # 设置PID/VID
    pPidBuf = ctypes.c_ushort(0x5838)
    pVidBuf = ctypes.c_ushort(0x0211)
    p_xyz_di.LenaDDI_SetPidVid(XYZ_Cam, ctypes.byref(XYZ_Cam_Info), ctypes.byref(pPidBuf), ctypes.byref(pVidBuf))


# 对应 main.cpp 中 void ExposureSet(void) 功能是设备初始化
def ExposureSet():
    global XYZ_Cam, XYZ_Cam_Info
    Exposure_Time = 30.0  # 设置曝光时间，单位为毫秒
    Exposure_Gain = 1.5  # 设置增益值

    if Camera_Model == 0:
        sensorType = SENSOR_TYPE_NAME.AR0135  # 相机曝光芯片型号为AR0135
    else:
        sensorType = SENSOR_TYPE_NAME.H65  # 相机曝光芯片型号为H65

    # 设置相机类型
    p_xyz_di.LenaDDI_SetSensorTypeName(XYZ_Cam, ctypes.c_int(sensorType.value))

    # 设置相机工作在自动曝光
    p_xyz_di.LenaDDI_EnableAE(XYZ_Cam, ctypes.byref(XYZ_Cam_Info))

    # p_xyz_di.LenaDDI_DisableAE(XYZ_Cam, ctypes.byref(XYZ_Cam_Info))

    # 设置增益
    # p_xyz_di.LenaDDI_SetGlobalGain(XYZ_Cam, ctypes.byref(XYZ_Cam_Info), ctypes.c_int(2), ctypes.c_float(Exposure_Gain))

    # 设置曝光时间
    # p_xyz_di.LenaDDI_SetExposureTime(XYZ_Cam, ctypes.byref(XYZ_Cam_Info), ctypes.c_int(2), ctypes.c_float(Exposure_Time))


####################################################第三部分关于设备返回数据的处理###########################################
# 在回调函数中用到 对应 P_XYZ_Common.h 中 LenaDDIImageType
class LenaDDIImageType(Enum):
    IMAGE_UNKNOWN = -1
    COLOR_YUY2 = 0
    COLOR_RGB24 = 1
    COLOR_MJPG = 2
    DEPTH_8BITS = 100
    DEPTH_8BITS_0x80 = 101
    DEPTH_11BITS = 102
    DEPTH_10BITS = 103

    @staticmethod
    def IsImageColor(img_type):
        return img_type in (LenaDDIImageType.COLOR_YUY2,
                            LenaDDIImageType.COLOR_RGB24,
                            LenaDDIImageType.COLOR_MJPG)

    @staticmethod
    def IsImageDepth(img_type):
        return img_type not in (LenaDDIImageType.IMAGE_UNKNOWN,
                                LenaDDIImageType.IsImageColor(img_type))


# 生成深度数据和彩虹图形的映射表 对应 Test.cpp 中 void ColorMap(double k, double& R, double& G, double& B)
def color_map(k):
    if k < 0.0: k = 0.0
    if k > 1.0: k = 1.0
    if k < 0.1:
        r = k / 0.1
        R = G = B = 128.0 + r * 127.0
    elif k < 0.2:
        k -= .1
        r = k / 0.1
        R = 255.0
        G = B = (1.0 - r) * 255.0
    elif k < 0.35:
        k -= .2
        r = k / 0.15
        B = 0.0
        G = r * 255.0
        R = 255.0
    elif k < 0.5:
        k -= 0.35
        r = k / 0.15
        B = 0.0
        G = (1.0 - r / 4.0) * 255.0
        R = (1.0 - r / 2.0) * 255.0
    elif k < 0.6:
        k -= 0.5
        r = k / 0.1
        B = r * 128.0
        G = 196.0
        R = (1.0 - r) * 128.0
    elif k < 0.7:
        k -= 0.6
        r = k / 0.1
        B = 128.0 + r * 127.0
        G = 196.0
        R = 0.0
    elif k < 0.8:
        k -= 0.7
        r = k / 0.1
        B = 255
        G = (1.0 - r) * 196.0
        R = 0
    elif k < 0.9:
        k -= 0.8
        r = k / 0.1
        B = (1.0 - r / 2.0) * 255.0
        G = 0.0
        R = r * 128.0
    else:
        k -= .9
        r = k / .1
        R = B = (1 - r) * 128
        G = 0
    return np.array([B, G, R], dtype=np.uint8)


# 对应 Test.cpp 中void DmColorMode11(RGBQUAD *pallete, int mode)
def dm_color_mode11(mode):
    if mode == 1:
        t1 = 512
        t2 = 1024
    elif mode == 2:
        t1 = 200
        t2 = 512
    elif mode == 3:
        t1 = 5
        t2 = 256
    else:
        t1 = 256
        t2 = 512
    m = (0.75 - 1.0) / t1
    b = 1.0
    pallete = [color_map(m * i + b) for i in range(t1)]
    m = (0.25 - 0.75) / (t2 - t1)
    b = 0.75 - m * t1
    pallete += [color_map(m * i + b) for i in range(t1, t2)]
    m = (0 - 0.25) / (2048 - t2)
    b = 0.25 - m * t2
    pallete += [color_map(m * i + b) for i in range(t2, 2048)]
    return np.array(pallete)


# 对应 Test.cpp 中void UpdateD11DisplayImage_DIB24(RGBQUAD *pColorPaletteD11, BYTE *pDepthD11, BYTE *pDepthDIB24, int cx, int cy) python算法的方式不同与c++中使用循环的方式进行映射
# python优化使用pDepthD11作为索引数组来一次性从pColorPaletteD11中检索所有对应的颜色值，再通过广播机制将检索到的颜色数组一次性赋值给pDepthDIB24，numpy库底层采用了c语音来处理，大大提高了数据处理速度。
def update_d11_display_image_dib24_optimized(pColorPaletteD11, pDepthD11, pDepthDIB24, cx, cy):
    nBPS = ((cx * 3 + 3) // 4) * 4
    pDepthD11 = pDepthD11.reshape(cy, cx)
    pDepthDIB24 = pDepthDIB24.reshape(cy, nBPS // 3, 3)
    pDepthDIB24[:] = pColorPaletteD11[pDepthD11]
    return pDepthDIB24


# 与c++中没有固定的对应关系，其作用是封装
def process_color_image(img_buf, width, height):
    # 将原始图像缓冲区转换为具有指定形状的NumPy数组。
    # 形状指示图像具有'height'行，'width'列，以及3个颜色通道（RGB）。
    img_array = np.ctypeslib.as_array(img_buf, shape=(height, width, 3))

    # 将图像的颜色空间从RGB（红，绿，蓝）转换为BGR（蓝，绿，红）。
    # OpenCV通常使用BGR作为其默认颜色顺序，因此这里进行转换以适配OpenCV处理图像。
    img = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)

    # 对图像进行翻转操作。
    # 0表示沿x轴翻转，即上下翻转图像。
    img = cv2.flip(img, 0)

    # 再次将图像的颜色空间从BGR转换回RGB。
    # 这样做是为了恢复原始的颜色顺序，可能是为了显示或进一步处理。
    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

    # 返回处理后的图像。
    return img


# 获取颜色调色板，程序初始化时执行一次就可以了
color_palette = dm_color_mode11(mode=0)  # 这里的模式可以根据实际情况进行调整


# 对应main.cpp 中 void Depth_Img::Depth_Read(BYTE* buf)
def process_depth_image(img_buf, width, height):
    global depth_img_in
    # 从指针创建 numpy 数组
    img_arr = np.ctypeslib.as_array(
        (ctypes.c_uint16 * (width * height)).from_address(ctypes.addressof(img_buf.contents)))
    # 将一维数组转化为2D深度图像
    depth_img_in = img_arr.reshape((height, width))

    # 创建一个空的RGB图像（24位，3通道）
    rgb_img = np.zeros((height, width, 3), dtype=np.uint8)

    # 更新显示图像
    rgb_img = update_d11_display_image_dib24_optimized(color_palette, depth_img_in, rgb_img, width, height)

    return rgb_img


# 回调函数
# 对应main.cpp 中 void ImageProcess(void) callback函数
@ctypes.CFUNCTYPE(None, ctypes.c_int, ctypes.c_int, ctypes.POINTER(ctypes.c_ubyte), ctypes.c_int, ctypes.c_int,
                  ctypes.c_int, ctypes.c_int, ctypes.c_void_p)
def callback_fn(img_type, img_id, img_buf, img_size, width, height, serial_number, user_param):
    global color_img, depth_img, color_new_flag, depth_new_flag
    img_type = LenaDDIImageType(img_type)

    if LenaDDIImageType.IsImageColor(img_type) and color_new_flag is False:
        try:
            color_img = process_color_image(img_buf, width, height)
            color_new_flag = True
        except Exception as e:
            pass
            # logging.info(
            #     f"Cv IsImageColor :callback_fn;img_type:{img_type},img_buf:{img_buf},width:{width},height:{height}")
            # logging.info(f"{e}")

    elif LenaDDIImageType.IsImageDepth(img_type) and depth_new_flag is False and width > 0 and height > 0:
        try:
            depth_img = process_depth_image(img_buf, width, height)
            depth_new_flag = True
        except Exception as e:
            pass
            # logging.info(
            #     f"Cv IsImageDepth :callback_fn;img_type:{img_type},img_buf:{img_buf},width:{width},height:{height}")
            # logging.info(f"{e}")
    return 0


# 鼠标回调函数 对应main.cpp 中 void Key_Response(void)
def key_response():
    global num  # 如果num在函数外定义，需要使用global关键字来修改它

    # 保存原图、用作观察的彩色深度图、深度图原始数据三张图像
    file_name = f"data/Image_Color{num}.jpg"
    cv2.imwrite(file_name, color_img)
    file_name = f"data/Image_Depth_Display{num}.jpg"
    cv2.imwrite(file_name, depth_img)
    file_name = f"data/Image_Depth_Raw{num}.png"
    cv2.imwrite(file_name, depth_img_in)
    num += 1

    # 在命令行中显示十字线中心所在位置的RGB数值以及XYZ三维坐标
    print()
    print(f"Cross_Point Value of R-G-B: ({RGB_R}, {RGB_G}, {RGB_B})")
    print(f"Cross_Point Value of X-Y-Z in World Coordinate (unit: mm): ({Pos_x}, {Pos_y}, {Pos_z})")


# 对应 Mouse_click.h 中 static void onMouse(int event, int x, int y, int, void*)
def onMouse(event, x, y, flags, param):
    global Mouse_Point, Mouse_selectObject, Mouse_selection, cross_x, cross_y

    if Mouse_selectObject:
        Mouse_selection[0] = min(x, Mouse_Point[0])
        Mouse_selection[1] = min(y, Mouse_Point[1])
        Mouse_selection[2] = abs(x - Mouse_Point[0])
        Mouse_selection[3] = abs(y - Mouse_Point[1])

    if event == cv2.EVENT_LBUTTONDOWN:  # 鼠标左键按下
        Mouse_Point = (x, y)
        Mouse_selection = [x, y, 0, 0]
        Mouse_selectObject = True
        if y < 360 and x < 640:
            cross_x, cross_y = x, y
            # 应用特定的边界条件
            if cross_y == 359: cross_y = 358
            if cross_y == 0:   cross_y = 1
            if cross_x == 639: cross_x = 638
            if cross_x == 0:   cross_x = 1

    elif event == cv2.EVENT_LBUTTONUP:  # 鼠标左键释放
        Mouse_selectObject = False
        if Mouse_selection[2] > 0 and Mouse_selection[3] > 0:
            # 如有必要，请在此处处理选择逻辑
            pass


# 对应 main.cpp 中 void ImageProcess(void)
def ImageProcess():
    global color_img, depth_img, cross_x, cross_y, num, Pos_x, Pos_y, Pos_z, RGB_R, RGB_G, RGB_B, resize_dims, resize_dims, XYZ_Cam_Color_Option
    global color_new_flag, depth_new_flag, color_img_resized, depth_img_resized

    # 确保我们有新的图像要处理
    if not color_new_flag or not depth_new_flag:
        return

    # 将十字位置转换为全尺寸图像坐标
    cross_x_full = cross_x * 2
    cross_y_full = cross_y * 2

    # 读取十字位置的颜色值
    RGB_B, RGB_G, RGB_R = color_img[cross_y_full, cross_x_full]

    # 十字位置的EAD Depth值并计算十字周围的平均深度
    depth_values = depth_img_in[cross_y_full - 1:cross_y_full + 2, cross_x_full - 1:cross_x_full + 2]

    depth_values_nonzero = depth_values[depth_values > 0]  # 选择非零值

    if depth_values_nonzero.size > 0:  # 检查数组是否非空
        Pos_z = np.mean(depth_values_nonzero)
    else:
        Pos_z = 0  # 如果没有非零值，则设置默认值


    # 计算3D位置(Pos_x、Pos_y、Pos_z，单位为mm)
    if Pos_z != 0:
        Pos_z = 8 * Focus_Pixel * BaseLine / Pos_z

        if Pos_z > 23689:
            Pos_z = 1.2563*Pos_z - 4511.2
        elif Pos_z > 11528:
            Pos_z = 1.0384 * Pos_z + 133.09
        else:
            Pos_z = 1.0329 * Pos_z - 35.261

        Pos_x = (cross_x_full - ccpoint_LX) * Pos_z / Focus_Pixel
        Pos_y = (cross_y_full - ccpoint_LY) * Pos_z / Focus_Pixel
    else:
        Pos_x = Pos_y = Pos_z = 0

    # 调整图像大小以进行显示
    if XYZ_Cam_Color_Option == 0:
        color_img_resized = cv2.resize(color_img, resize_dims)
        depth_img_resized = cv2.resize(depth_img, resize_dims)
    else:
        color_img_resized = cv2.resize(color_img, resize_dims2)
        depth_img_resized = cv2.resize(depth_img, resize_dims)

    h, w = color_img_resized.shape[:2]
    img_color = (255, 255, 255)

    # 在图像上画交叉线
    # 在图像上绘制十字线
    cv2.line(color_img_resized, (cross_x, 0), (cross_x, h), img_color, 1)
    cv2.line(color_img_resized, (cross_x, h - 1), (cross_x, 0), img_color, 1)
    cv2.line(color_img_resized, (0, cross_y), (w, cross_y), img_color, 1)
    cv2.line(color_img_resized, (w - 1, cross_y), (0, cross_y), img_color, 1)
    cv2.line(color_img_resized, (cross_x - 10, cross_y), (cross_x + 10, cross_y), img_color, 1)
    cv2.line(color_img_resized, (cross_x, cross_y - 10), (cross_x, cross_y + 10), img_color, 1)

    cv2.line(depth_img_resized, (cross_x, 0), (cross_x, h), img_color, 1)
    cv2.line(depth_img_resized, (cross_x, h - 1), (cross_x, 0), img_color, 1)
    cv2.line(depth_img_resized, (0, cross_y), (w, cross_y), img_color, 1)
    cv2.line(depth_img_resized, (w - 1, cross_y), (0, cross_y), img_color, 1)
    cv2.line(depth_img_resized, (cross_x - 10, cross_y), (cross_x + 10, cross_y), img_color, 1)
    cv2.line(depth_img_resized, (cross_x, cross_y - 10), (cross_x, cross_y + 10), img_color, 1)

    # 显示图像

    cv2.imshow('Color Image', color_img_resized)
    cv2.imshow('Depth Image', depth_img_resized)
    cv2.namedWindow('Color Image')
    cv2.namedWindow('Depth Image')


if __name__ == '__main__':
    # 程序报错打印
    log_dir = os.path.join(os.getcwd(), 'error')
    if not os.path.exists(log_dir):
        os.mkdir(log_dir)
    cgitb.enable(format='text', logdir=log_dir)

    # 打印设备信息
    devices = get_lena_ddi_devices()
    if devices:
        for device in devices:
            # 直接解码bytes对象
            device_name = device.strDevName.decode('utf-8').rstrip('\x00')
            logging.info(f"设备: wPID={device.wPID}, wVID={device.wVID}, strDevName={device_name}")

    # 初始化设备
    DeviceInit()
    # 曝光设置
    ExposureSet()
    key_flag = 0
    # 主处理回路
    while True:
        key = cv2.waitKey(1)
        if key_flag == 0:
            if depth_new_flag is True and depth_new_flag is True:
                ImageProcess()
                cv2.setMouseCallback('Color Image', onMouse)
                # 重置新的图像标志
                color_new_flag = False
                depth_new_flag = False
        if chr(key & 0xFF).lower() == 'c':
            key_response()
            # cv2.imwrite('captured_image.jpg', depth_img_in)  # 保存图像
            # print('Image captured and saved!')
        elif chr(key & 0xFF).lower() == 'q':
            break

    cv2.destroyAllWindows()