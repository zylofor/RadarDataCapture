close all;
%% 修改以下信息！Start


bin_path = 'D:\\UAV\\20260714\\';%1
% save_path = '\\three\\';%2
% if ~isfolder(strcat(bin_path,save_path))
%     mkdir(bin_path);
% end  
if ~isfolder(strcat(bin_path))
    mkdir(bin_path);
end  
single_count = '_3003';
bin_name = strcat('_0_scut_000_rain','_azimuth');%3
start_time_str = strcat('2026','0715','17','1730');%4
start_time_datetime = datetime(start_time_str, 'Format', 'yyyyMMddHHmmss');
% bin_name = strcat(save_path,int2str(hour(start_time_datetime)),'_',int2str(minute(start_time_datetime)),'_',int2str(second(start_time_datetime, 'secondofminute')),bin_name);
bin_name = strcat(int2str(hour(start_time_datetime)),'_',int2str(minute(start_time_datetime)),'_',int2str(second(start_time_datetime, 'secondofminute')),bin_name);
%5两台电脑时间同步，尽量不超过1S
syn_delay_time = -0.1; %慢减快加

%6
%依据电脑内存选择保存视频分辨率
vid = videoinput('winvideo', 2, 'MJPG_1280x720');
vid.ReturnedColorSpace = 'rgb';
vid.ROIPosition = [0 0 1280 720];

%% End

start_time_datetime = datetime(start_time_str, 'Format', 'yyyyMMddHHmmss') + seconds(syn_delay_time); 

% 设置帧率
desired_frame_rate = 10;  
% 设置捕捉总时间（秒） 
capture_duration = 30; % 注意检查雷达采集的时间

% video_name = bin_name(8:end);
% video_path = strcat(bin_path,save_path,'videos\\');
video_name = bin_name;
video_path = strcat(bin_path,'videos\\');

if ~exist(video_path, 'dir')
    mkdir(video_path);
end

% 打开视频对象
% vid = videoinput('winvideo', 2, 'MJPG_1280x720');
% vid.ReturnedColorSpace = 'rgb';
% vid.ROIPosition = [0 0 1280 720];
set(vid, 'FramesPerTrigger', 1);
set(vid, 'TriggerRepeat', Inf);

vidObj = VideoWriter([video_path, video_name,'.avi']);
vidObj.FrameRate = desired_frame_rate;
open(vidObj);

numFrames = 30 * capture_duration + 15;
frames = cell(numFrames, 1);
frameInterval = 1 / 30;

% 等待时间开始
while datetime('now', 'Format', 'yyyyMMddHHmmss') < start_time_datetime
    %disp(datetime('now', 'Format', 'yyyyMMddHHmmss'))
    continue; % 没到时间前，一直循环
end


%% 打印摄像头开始时间
% 获取当前日期和时间，包括毫秒
currentDateTime = datetime('now', 'Format', 'yyyy-MM-dd HH:mm:ss.SSS');
% 打印当前时间，包括毫秒
fprintf('\n------------VideoCapture------------\n');
fprintf('摄像头当前时间: %s\n正在捕捉视频...\n', char(currentDateTime));

start(vid);

SendCaptureCMD_path(bin_path, bin_name);

for i = 1:numFrames
    frames{i} = getdata(vid, 1);
    pause(frameInterval);
end

fprintf('----\n正在保存视频');

for i = 16:numFrames
    if mod(i-15, 3) == 0
        writeVideo(vidObj, frames{i});
    end
end

%% 打印视频保存路径
[upPath,~]=fileparts(mfilename('fullpath')); % upPath为当前.m文件所在文件夹
fprintf('----\n视频采集完成！\n视频文件保存路径：\n');
disp([upPath,'\', video_path, video_name, '.mp4', newline]);

%% 关闭视频对象和摄像头
stop(vid);
delete(vid);
clear vid;
imaqreset;

frames = [];
clear frames;

close(vidObj);
delete(vidObj);
clear vidObj;

close all;