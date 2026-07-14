%% 本文件用于 定时开始 调用采集雷达数据的命令
%% 要采集数据时，运行该文件！

%% 设置开始时间
Param = ParamObject();

start_time_str = Param.start_time;
start_time_datetime = datetime(start_time_str, 'Format', 'yyyyMMddHHmmss')...
                      +seconds(Param.delay_time); % 延迟启动
disp(['开始时间: ', start_time_str]);
% 等待开始
while datetime('now', 'Format', 'yyyyMMddHHmmssSSS') < start_time_datetime
    continue; % 没到时间前，一直循环
end

%% 发送采集雷达数据的命令
%SendCaptureCMD('Action');
%SendCaptureCMD3('G:\MyDataset\DatasetFile\Action');
bin_name = Param.bin_name;
bin_path = Param.bin_path;
% 第一个输入参数是bin文件要保存的文件夹，注意有2个斜杠
SendCaptureCMD_path(bin_path, bin_name);