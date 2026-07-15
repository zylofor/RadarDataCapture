import ctypes
from ctypes import POINTER, c_void_p, c_ushort, c_char, c_long, c_bool, c_int
import cgitb
import logging
import cv2
import os
import numpy as np
from enum import Enum
import time
import datetime


# --- 原有结构体定义保持不变 ---
class DEVSELINFO(ctypes.Structure):
    _fields_ = [("index", c_long)]


class DEVINFORMATIONEX(ctypes.Structure):
    _fields_ = [
        ("wPID", c_ushort),
        ("wVID", c_ushort),
        ("strDevName", c_char * 512),
        ("nChpID", c_ushort),
        ("nDevType", c_ushort)
    ]


class LenaDDI_STREAM_INFO(ctypes.Structure):
    _fields_ = [
        ("nWidth", c_int),
        ("nHeight", c_int),
        ("bFormatMJPG", c_int),
    ]


class SENSOR_TYPE_NAME(Enum):
    H65 = 0
    H65_TEMP = 1
    AR0135_TEMP = 2
    AR0135 = 3


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


# --- 回调函数保持不变 ---
@ctypes.CFUNCTYPE(None, ctypes.c_int, ctypes.c_int, ctypes.POINTER(ctypes.c_ubyte), ctypes.c_int, ctypes.c_int,
                  ctypes.c_int, ctypes.c_int, ctypes.c_void_p)
def callback_fn(img_type, img_id, img_buf, img_size, width, height, serial_number, user_param):
    img_type = LenaDDIImageType(img_type)

    if LenaDDIImageType.IsImageColor(img_type) and depthCapture.color_new_flag is False:
        try:
            depthCapture.color_img = depthCapture.process_color_image(img_buf, width, height)
            depthCapture.color_new_flag = True
        except Exception as e:
            logging.info(f"Cv IsImageColor Error: {e}")

    elif LenaDDIImageType.IsImageDepth(img_type) and depthCapture.depth_new_flag is False and width > 0 and height > 0:
        try:
            depthCapture.depth_img = depthCapture.process_depth_image(img_buf, width, height)
            depthCapture.depth_new_flag = True
        except Exception as e:
            logging.info(f"Cv IsImageDepth Error: {e}")
    return 0


class DepthCapture:
    def __init__(self):
        # --- 全局变量与设备相关 ---
        self.XYZ_Cam = c_void_p()
        self.XYZ_Cam_Index = 0
        self.XYZ_Cam_Info = DEVSELINFO()
        self.XYZ_Cam_Color_Resolution = (LenaDDI_STREAM_INFO * 64)()
        self.XYZ_Cam_Depth_Resolution = (LenaDDI_STREAM_INFO * 64)()
        self.usb3_0 = False
        self.m_depthType = 4
        self.XYZ_Cam_Color_Option = 0
        self.Camera_Model = 0
        self.XYZ_Cam_Rectify_Option = 0
        self.Depth_Data_Type = 0

        # --- 图像数据容器 ---
        self.color_img = None
        self.depth_img = None
        self.color_new_flag = False
        self.depth_new_flag = False
        self.color_img_resized = None
        self.depth_img_resized = None
        self.depth_img_in = None

        # --- 图像处理参数 ---
        self.cross_x, self.cross_y = 320, 180
        self.num = 0

        # --- 相机参数 ---
        self.fps = 10                  # 目标帧率：10 FPS
        self.ccpoint_LX, self.ccpoint_LY = 642, 361
        self.Focus_Pixel = 1200
        self.BaseLine = 179.721
        self.resize_dims = (640, 360)
        self.resize_dims2 = (1280, 360)
        self.Pos_x = 0
        self.Pos_y = 0
        self.Pos_z = 0
        self.RGB_R = 0
        self.RGB_G = 0
        self.RGB_B = 0
        self.Mouse_Point = (0, 0)
        self.Mouse_selectObject = False
        self.Mouse_selection = [0, 0, 0, 0]

        self.color_palette = self.dm_color_mode11(mode=0)

        # --- 保存相关设置 ---
        self.open_window = False  # False为采集模式，True为观察模式

        self.rgb_buffer = []        
        self.depth_vis_buffer = []  
        self.depth_raw_buffer = []  

        self.base_save_dir = "D:/DataCapture/{}"

        # 设置采集时间（可根据实际需求修改）
        self.save_start_dt = datetime.datetime(2026, 7, 15, 17, 43, 00)
        self.save_duration = 30  # 保存时长 (秒)
        self.target_frames = self.fps * self.save_duration  # 10 * 30 = 300 帧
        
        # [修复核心1] 计算采样帧间隔（1.0 / 10 = 0.1秒）
        self.frame_interval = 1.0 / self.fps
        
        self.save_start_time = time.mktime(self.save_start_dt.timetuple())
        self.save_end_time = self.save_start_time + self.save_duration

        if self.open_window is False:
            dir_name = self.save_start_dt.strftime("%Y%m%d_%H%M%S")
            self.current_save_dir = self.base_save_dir.replace("{}", dir_name, 1)
            os.makedirs(self.current_save_dir, exist_ok=True)
            print(f"数据将保存至: {self.current_save_dir}")
            print(f"设定参数：目标 {self.fps} 帧/秒 (每 {self.frame_interval} 秒抽帧一次), 采集 {self.save_duration} 秒, 目标总帧数: {self.target_frames} 帧")

    def DeviceInit(self):
        to_rgb = True
        depth_stream_index = 0
        depth_stream_switch = 2
        callback_param = None

        p_xyz_di.LenaDDI_Init2(ctypes.byref(self.XYZ_Cam), False, True)
        self.XYZ_Cam_Info.index = self.XYZ_Cam_Index

        p_xyz_di.LenaDDI_GetDeviceResolutionList(self.XYZ_Cam, ctypes.byref(self.XYZ_Cam_Info), 64,
                                                 self.XYZ_Cam_Color_Resolution, 64,
                                                 self.XYZ_Cam_Depth_Resolution)

        if self.XYZ_Cam_Depth_Resolution[0].nWidth == 1280:
            self.usb3_0 = True

        if self.usb3_0:
            if self.Depth_Data_Type == 0:
                if self.XYZ_Cam_Rectify_Option == 0:
                    self.m_depthType = 4
                else:
                    self.m_depthType = 9

        p_xyz_di.LenaDDI_SetDepthDataType(self.XYZ_Cam, ctypes.byref(self.XYZ_Cam_Info), ctypes.c_int(self.m_depthType))

        fps = ctypes.c_int(self.fps)
        ret = p_xyz_di.LenaDDI_OpenDeviceEx(
            self.XYZ_Cam, ctypes.byref(self.XYZ_Cam_Info), ctypes.c_int(self.XYZ_Cam_Color_Option),
            to_rgb, depth_stream_index, depth_stream_switch,
            callback_fn, callback_param, ctypes.byref(fps), ctypes.c_int(0)
        )
        print(f"Device Open Ret: {ret}, FPS Request: {fps.value} (注意: 硬件可能会忽略此设置并以30FPS运行，依赖软件抽帧控制)")

        pPidBuf = ctypes.c_ushort(0x5838)
        pVidBuf = ctypes.c_ushort(0x0211)
        p_xyz_di.LenaDDI_SetPidVid(self.XYZ_Cam, ctypes.byref(self.XYZ_Cam_Info), ctypes.byref(pPidBuf),
                                   ctypes.byref(pVidBuf))

    def ExposureSet(self):
        Exposure_Time = 30.0
        Exposure_Gain = 1.5

        if self.Camera_Model == 0:
            sensorType = SENSOR_TYPE_NAME.AR0135
        else:
            sensorType = SENSOR_TYPE_NAME.H65

        p_xyz_di.LenaDDI_SetSensorTypeName(self.XYZ_Cam, ctypes.c_int(sensorType.value))
        p_xyz_di.LenaDDI_EnableAE(self.XYZ_Cam, ctypes.byref(self.XYZ_Cam_Info))

    def color_map(self, k):
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

    def dm_color_mode11(self, mode):
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
        pallete = [self.color_map(m * i + b) for i in range(t1)]
        m = (0.25 - 0.75) / (t2 - t1)
        b = 0.75 - m * t1
        pallete += [self.color_map(m * i + b) for i in range(t1, t2)]
        m = (0 - 0.25) / (2048 - t2)
        b = 0.25 - m * t2
        pallete += [self.color_map(m * i + b) for i in range(t2, 2048)]
        return np.array(pallete)

    def update_d11_display_image_dib24_optimized(self, pColorPaletteD11, pDepthD11, pDepthDIB24, cx, cy):
        nBPS = ((cx * 3 + 3) // 4) * 4
        pDepthD11 = pDepthD11.reshape(cy, cx)
        pDepthDIB24 = pDepthDIB24.reshape(cy, nBPS // 3, 3)
        pDepthDIB24[:] = pColorPaletteD11[pDepthD11]
        return pDepthDIB24

    def process_color_image(self, img_buf, width, height):
        img_array = np.ctypeslib.as_array(img_buf, shape=(height, width, 3))
        img = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
        img = cv2.flip(img, 0)
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        return img

    def process_depth_image(self, img_buf, width, height):
        img_arr = np.ctypeslib.as_array(
            (ctypes.c_uint16 * (width * height)).from_address(ctypes.addressof(img_buf.contents)))
        self.depth_img_in = img_arr.reshape((height, width))
        rgb_img = np.zeros((height, width, 3), dtype=np.uint8)
        rgb_img = self.update_d11_display_image_dib24_optimized(self.color_palette, self.depth_img_in, rgb_img, width, height)
        return rgb_img

    def onMouse(self, event, x, y, flags, param):
        if self.Mouse_selectObject:
            self.Mouse_selection[0] = min(x, self.Mouse_Point[0])
            self.Mouse_selection[1] = min(y, self.Mouse_Point[1])
            self.Mouse_selection[2] = abs(x - self.Mouse_Point[0])
            self.Mouse_selection[3] = abs(y - self.Mouse_Point[1])

        if event == cv2.EVENT_LBUTTONDOWN:
            self.Mouse_Point = (x, y)
            self.Mouse_selection = [x, y, 0, 0]
            self.Mouse_selectObject = True
            if y < 360 and x < 640:
                self.cross_x, self.cross_y = x, y
                if self.cross_y == 359: self.cross_y = 358
                if self.cross_y == 0:   self.cross_y = 1
                if self.cross_x == 639: self.cross_x = 638
                if self.cross_x == 0:   self.cross_x = 1
        elif event == cv2.EVENT_LBUTTONUP:
            self.Mouse_selectObject = False

    def ImageProcess(self):
        if not self.color_new_flag or not self.depth_new_flag:
            return

        cross_x_full = self.cross_x * 2
        cross_y_full = self.cross_y * 2

        self.RGB_B, self.RGB_G, self.RGB_R = self.color_img[cross_y_full, cross_x_full]
        depth_values = self.depth_img_in[cross_y_full - 1:cross_y_full + 2, cross_x_full - 1:cross_x_full + 2]
        depth_values_nonzero = depth_values[depth_values > 0]

        if depth_values_nonzero.size > 0:
            self.Pos_z = np.mean(depth_values_nonzero)
        else:
            self.Pos_z = 0

        if self.Pos_z != 0:
            self.Pos_z = 8 * self.Focus_Pixel * self.BaseLine / self.Pos_z
            if self.Pos_z > 23689:
                self.Pos_z = 1.2563 * self.Pos_z - 4511.2
            elif self.Pos_z > 11528:
                self.Pos_z = 1.0384 * self.Pos_z + 133.09
            else:
                self.Pos_z = 1.0329 * self.Pos_z - 35.261

            self.Pos_x = (cross_x_full - self.ccpoint_LX) * self.Pos_z / self.Focus_Pixel
            self.Pos_y = (cross_y_full - self.ccpoint_LY) * self.Pos_z / self.Focus_Pixel
        else:
            self.Pos_x = self.Pos_y = self.Pos_z = 0

        if self.XYZ_Cam_Color_Option == 0:
            self.color_img_resized = cv2.resize(self.color_img, self.resize_dims)
            self.depth_img_resized = cv2.resize(self.depth_img, self.resize_dims)
        else:
            self.color_img_resized = cv2.resize(self.color_img, self.resize_dims2)
            self.depth_img_resized = cv2.resize(self.depth_img, self.resize_dims)

        h, w = self.color_img_resized.shape[:2]
        img_color = (255, 255, 255)

        cv2.line(self.color_img_resized, (self.cross_x, 0), (self.cross_x, h), img_color, 1)
        cv2.line(self.color_img_resized, (0, self.cross_y), (w, self.cross_y), img_color, 1)
        cv2.line(self.color_img_resized, (self.cross_x - 10, self.cross_y), (self.cross_x + 10, self.cross_y), img_color, 1)

        cv2.line(self.depth_img_resized, (self.cross_x, 0), (self.cross_x, h), img_color, 1)
        cv2.line(self.depth_img_resized, (0, self.cross_y), (w, self.cross_y), img_color, 1)
        cv2.line(self.depth_img_resized, (self.cross_x - 10, self.cross_y), (self.cross_x + 10, self.cross_y), img_color, 1)

        cv2.imshow('Color Image', self.color_img_resized)
        cv2.imshow('Depth Image', self.depth_img_resized)
        cv2.namedWindow('Color Image')
        cv2.namedWindow('Depth Image')

    def convert_raw_depth_to_xyz_map(self, raw_depth):
        h, w = raw_depth.shape
        u_grid, v_grid = np.meshgrid(np.arange(w), np.arange(h))
        
        valid_mask = raw_depth > 0
        Z = np.zeros((h, w), dtype=np.float32)
        
        raw_valid = raw_depth[valid_mask].astype(np.float32)
        Z_valid = 8.0 * self.Focus_Pixel * self.BaseLine / raw_valid
        
        cond1 = Z_valid > 23689
        cond2 = (Z_valid > 11528) & ~cond1
        cond3 = ~cond1 & ~cond2
        
        Z_valid[cond1] = 1.2563 * Z_valid[cond1] - 4511.2
        Z_valid[cond2] = 1.0384 * Z_valid[cond2] + 133.09
        Z_valid[cond3] = 1.0329 * Z_valid[cond3] - 35.261
        
        Z[valid_mask] = Z_valid
        
        X = np.zeros((h, w), dtype=np.float32)
        Y = np.zeros((h, w), dtype=np.float32)
        X[valid_mask] = (u_grid[valid_mask] - self.ccpoint_LX) * Z[valid_mask] / self.Focus_Pixel
        Y[valid_mask] = (v_grid[valid_mask] - self.ccpoint_LY) * Z[valid_mask] / self.Focus_Pixel
        
        return np.stack([X, Y, Z], axis=-1)

    # [修复核心2] 加入时间戳门限控制，彻底杜绝30FPS的硬件流快速灌满缓冲区
    def buffer_data(self, current_time):
        if self.color_img is not None and self.depth_img is not None and self.depth_img_in is not None:
            if len(self.rgb_buffer) < self.target_frames:
                # 计算下一帧按 10FPS 理论上应该出现的严格时间点
                # 这种计算方式完全消除了浮点数累加导致的“越采集越偏”的累计计时误差！
                expected_time = self.save_start_time + len(self.rgb_buffer) * self.frame_interval
                
                # 只有当前系统时间达到了理论采样点，才从底层30FPS的数据流中“抓取”一帧
                if current_time >= expected_time:
                    self.rgb_buffer.append(self.color_img.copy())
                    self.depth_vis_buffer.append(self.depth_img.copy())
                    self.depth_raw_buffer.append(self.depth_img_in.copy())
                    self.num = len(self.rgb_buffer)
                    if self.num % 10 == 0:
                        elapsed = current_time - self.save_start_time
                        print(f"进度: {self.num} / {self.target_frames} 帧 | 已耗时: {elapsed:.1f} 秒 (实际采样率: {self.num/elapsed:.2f} FPS)")

    def save_recording(self):
        if len(self.rgb_buffer) == 0:
            print("警告：缓冲区为空，未采集到数据。")
            return

        print(f"\n采集完成！共捕获准确帧数：{len(self.rgb_buffer)} 帧。开始生成视频和 3D npy 文件...")
        
        rgb_video_path = os.path.join(self.current_save_dir, "rgb_video.mp4")
        depth_video_path = os.path.join(self.current_save_dir, "depth_vis_video.mp4")
        npy_save_dir = os.path.join(self.current_save_dir, "depth_xyz_mm_frames")
        os.makedirs(npy_save_dir, exist_ok=True)

        h, w, _ = self.rgb_buffer[0].shape
        fourcc = cv2.VideoWriter_fourcc(*'MJPG')
        # 视频按照你要求设定的 10 FPS 写入，300帧正好是 30.0 秒播放时长
        out_rgb = cv2.VideoWriter(rgb_video_path, fourcc, self.fps, (w, h))

        h_d, w_d, _ = self.depth_vis_buffer[0].shape
        out_depth = cv2.VideoWriter(depth_video_path, fourcc, self.fps, (w_d, h_d))

        for i in range(len(self.rgb_buffer)):
            out_rgb.write(self.rgb_buffer[i])
            out_depth.write(self.depth_vis_buffer[i])

            xyz_map = self.convert_raw_depth_to_xyz_map(self.depth_raw_buffer[i])
            npy_filename = os.path.join(npy_save_dir, f"frame_{i:04d}.npy")
            np.save(npy_filename, xyz_map)

        out_rgb.release()
        out_depth.release()
        print(f"视频已保存：\n  - {rgb_video_path}\n  - {depth_video_path}")
        print(f"物理三维坐标已按帧保存至目录：{npy_save_dir}")

        self.rgb_buffer = []
        self.depth_vis_buffer = []
        self.depth_raw_buffer = []

    def run(self):
        log_dir = os.path.join(os.getcwd(), 'error')
        if not os.path.exists(log_dir):
            os.mkdir(log_dir)
        cgitb.enable(format='text', logdir=log_dir)

        self.DeviceInit()
        self.ExposureSet()

        print("设备启动完毕，等待进入预设的时间采集窗口...")
        recording_done = False

        while True:
            now = time.time()

            if self.open_window is False:
                # 依然保持以实际采集满 300 帧作为唯一的最终终止条件
                if len(self.rgb_buffer) >= self.target_frames:
                    if not recording_done:
                        print(f"已精准采集满 {self.target_frames} 帧！停止数据接收。")
                        self.save_recording()
                        recording_done = True
                    break
                
                # 超时保护宽限：如果超出设定时长 5 秒仍未采满（比如电脑严重卡顿），强制保存退出
                if now > self.save_end_time + 5.0:
                    if not recording_done:
                        print(f"超出宽限时间，已采集 {len(self.rgb_buffer)} 帧，提前终止并保存...")
                        if len(self.rgb_buffer) > 0:
                            self.save_recording()
                        recording_done = True
                    break
            else:
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break

            if self.depth_new_flag is True and self.color_new_flag is True:
                if self.open_window is True:
                    self.ImageProcess()
                    cv2.setMouseCallback('Color Image', self.onMouse)
                else:
                    # [修复核心3] 只有时间达到起点后，将当前的时间戳传入抽帧函数进行过滤
                    if self.save_start_time <= now and len(self.rgb_buffer) < self.target_frames:
                        self.buffer_data(now)

                self.color_new_flag = False
                self.depth_new_flag = False

            time.sleep(0.001)


if __name__ == '__main__':
    logging.basicConfig(filemode='w', format='%(name)s - %(levelname)s - %(message)s', level=logging.INFO)
    dll_path = r"D:\博士研究生\实验\RGB-D教程\RGB-D\P_XYZ_DI.dll"

    try:
        p_xyz_di = ctypes.WinDLL(dll_path)
        depthCapture = DepthCapture()
        depthCapture.run()
    except OSError as e:
        print(f"错误: 无法加载 DLL。请检查路径: {dll_path}")
        print(e)
    except Exception as e:
        print(f"运行时错误: {e}")
