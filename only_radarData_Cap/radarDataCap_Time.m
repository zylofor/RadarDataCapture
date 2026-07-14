close all;
%% 修改以下信息！Start
bin_path = 'F:\\MyDataset\\DatasetFile\\UAV';
bin_name = strcat('_30_scut_211','_elevation');
capture_date = strcat('2025', '0106');
start_time_str = strcat(capture_date,'22','1100');
%% End

start_time_datetime = datetime(start_time_str, 'Format', 'yyyyMMddHHmmss');
bin_name = strcat('\\', capture_date, '\\', int2str(hour(start_time_datetime)),'_',int2str(minute(start_time_datetime)),'_',int2str(second(start_time_datetime, 'secondofminute')),bin_name);

if ~exist(strcat(bin_path, '\\', capture_date), 'dir')
    mkdir(strcat(bin_path, '\\', capture_date));
end

% 等待开始
while datetime('now', 'Format', 'yyyyMMddHHmmssSSS') < start_time_datetime
    continue; % 没到时间前，一直循环
end

SendCaptureCMD_path(bin_path, bin_name);