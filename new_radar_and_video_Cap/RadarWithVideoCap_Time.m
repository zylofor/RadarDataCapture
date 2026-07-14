close all;
%%
bin_path = 'F:\MyDataset\DatasetFile\UAV';
bin_name = strcat('\\241111\\adc_data_001_wyu_ts','_azimuth');
start_time = strcat('2024','1112','00','4420');
cap_duration = 30;
% 延迟启动时间
delay_time = 0.2;
% 代码暂停时间，需与雷达采集时间相同，便于观察采集是否结束
pause_time = 30;

start_time_str = start_time;
start_time_datetime = datetime(start_time_str, 'Format', 'yyyyMMddHHmmss')-seconds(delay_time); 

%% 视频文件参数设置

% 设置帧率
desired_frame_rate = 10;  
% 设置捕捉总时间（秒） 
capture_duration = cap_duration; % 注意检查雷达采集的时间

% 设置视频画布大小
frame_width = 1920;
frame_height = 1080;

%% 打开摄像头
video_name = bin_name(17:end);
video_path = strcat('D:\博士研究生\实验\雷达数据采集代码与脚本\new_radar_and_video_Cap\videos\');

if ~exist(video_path, 'dir')
    mkdir(video_path);
end

% 打开视频对象
vid = videoinput('winvideo', 1, 'MJPG_1920x1080');
vid.ReturnedColorSpace = 'rgb';
vid.ROIPosition = [0 0 1920 1080];
set(vid, 'FramesPerTrigger', 1);
set(vid, 'TriggerRepeat', Inf);


vidObj = VideoWriter([video_path, video_name,'.avi']);
vidObj.FrameRate = desired_frame_rate;
open(vidObj);

numFrames = 30 * capture_duration;
frames = cell(numFrames, 1);

% 等待时间开始
while datetime('now', 'Format', 'yyyyMMddHHmmss') < start_time_datetime
    if datetime('now', 'Format', 'yyyyMMddHHmmss') - 1 < start_time_datetime
        start(vid);
    end
    continue; % 没到时间前，一直循环
end

%% 打印摄像头开始时间
% 获取当前日期和时间，包括毫秒
currentDateTime = datetime('now', 'Format', 'yyyy-MM-dd HH:mm:ss.SSS');
% 打印当前时间，包括毫秒
fprintf('\n------------VideoCapture------------\n');
fprintf('摄像头当前时间: %s\n正在捕捉视频...\n', char(currentDateTime));

SendCaptureCMD_path(bin_path, bin_name);
pause(delay_time);

for i = 1:numFrames
    frames{i} = getdata(vid, 1);
    ts_time = datetime("now","Format","uuuu-MM-dd'T'HH:mm:ss.SSS");
    ts_time = minute(ts_time) * 60 + second(ts_time, 'secondofminute');
    while true
        te_time = datetime("now","Format","uuuu-MM-dd'T'HH:mm:ss.SSS");
        te_time = minute(te_time) * 60 + second(te_time, 'secondofminute');
        if te_time - ts_time >= 1 / 30
            break;
        end
    end
end

for i = 1:numFrames
    if mod(i, 30 / desired_frame_rate) == 0
        writeVideo(vidObj, frames{i});
    end
end

%% 打印视频保存路径
[upPath,~]=fileparts(mfilename('fullpath')); % upPath为当前.m文件所在文件夹
fprintf('----\n视频采集完成！\n视频文件保存路径：\n');
disp([upPath,'\', video_path, video_name, '.mp4', newline]);

%% 关闭视频对象和摄像头
clear frames;
stop(vid);
close(vidObj);
close all;





