%% =============================================================
%% 本文件用于循环采集雷达bin文件数据
%% 原理：
% 将采集命令放在一个for循环内，每次发送采集命令后暂停一段时间
% 暂停的时间需大于雷达采集时间约4秒
% 暂停过后再发送采集命令，以此循环
%% =============================================================
clc;clear;
%% 设置文件保存路径
data_name = 'Action';
root_path = 'G:\MyDataset\DatasetFile\'; % 根路径名称
data_path = strcat(root_path,data_name);
%mkdir(data_path); % 创建文件夹
bin_name = 'adc_data_test_'; % bin文件名前缀
bin_path = strcat(data_path,'\',bin_name);

%% 修改采集数据的脚本文件
for i = 1:2
    disp(['---------Capture ',num2str(i),'---------']); % title
    
    path = strcat('adc_data_path="G:\\MyDataset\\DatasetFile\\',data_name,'\\', bin_name, num2str(i), '.bin"'); % 设计bin文件目录
    str = [path,"ar1.CaptureCardConfig_StartRecord(adc_data_path, 1)","RSTD.Sleep(1000)","ar1.StartFrame()"];
    fid = fopen('C:\ti\mmwave_studio_02_01_01_00\mmWaveStudio\Scripts\CaptureData1243.lua','w');
    for n = 1:length(str)
        fprintf(fid,'%s\n',str(n));
    end
    fclose(fid); % 关闭文件

%% 配置雷达数据采集
    addpath(genpath('.\'))
    % Initialize mmWaveStudio .NET connection
    RSTD_DLL_Path = 'C:\ti\mmwave_studio_02_01_01_00\mmWaveStudio\Clients\RtttNetClientController\RtttNetClientAPI.dll';
    ErrStatus = Init_RSTD_Connection(RSTD_DLL_Path);
    if (ErrStatus ~= 30000)
        disp('Error inside Init_RSTD_Connection');
        return;
    end
    strFilename = 'C:\\ti\\mmwave_studio_02_01_01_00\\mmWaveStudio\\Scripts\\CaptureData1243.lua';
    Lua_String = sprintf('dofile("%s")',strFilename);
    ErrStatus = RtttNetClientAPI.RtttNetClient.SendCommand(Lua_String);
    
    % 输出文件保存路径及文件名
    fprintf('--\nData Path:\n');
    disp([bin_path, num2str(i), '.bin']);
    fprintf('---------------------------\n\n\n');
    
    % 让循环停顿一段时间，在雷达采集完数据后再启动下一次循环
    pause(7);

end
    


