function SendCaptureCMD_path(data_path, bin_name)
    %% 本文件用于 MATLAB发送指令给mmwave studio，控制DCA采集并回传数据
    %% 采集数据时不运行该文件！

    %% 输入参数说明
    % data_path为bin文件的保存文件夹，bin_name为设置的bin文件名(不含.bin，如\\adc_data_1)

    %% 设置成功后该文件一般不再需要改动
    % data_path = 'G:\\MyDataset\\DatasetFile\\Action';
    % bin_name = '\\adc_data_1'; % 实际文件会产生Raw_0的后缀

    % 检查文件夹是否存在，如果不存在则创建
    if ~isfolder(data_path)
        mkdir(data_path);
    end    

    %% mmWave Studio 安装目录
    Studio_path = 'D:\ti\mmwave_studio_02_01_01_00\mmWaveStudio';
    Studio_path_2 = 'D:\\ti\\mmwave_studio_02_01_01_00\\mmWaveStudio'; % 双斜杠形式


    %% 修改采集数据的脚本文件
    % 设计bin文件目录
    str1 = strcat('adc_data_path="',data_path, bin_name,'.bin"'); 

    str = [str1,"ar1.CaptureCardConfig_StartRecord(adc_data_path, 1)","RSTD.Sleep(1000)","ar1.StartFrame()"];
    fid = fopen(strcat(Studio_path, '\Scripts\FrameStart.lua'),'w');
    for i = 1:length(str)
        fprintf(fid,'%s\n',str(i));
    end
    fclose(fid); % 关闭文件
    
    %% 打印雷达采集数据的开始时间    
    fprintf('\n-------------SendCapCMD--------------\n');
    % 获取当前日期和时间，包括毫秒
    currentDateTime = datetime('now', 'Format', 'yyyy-MM-dd HH:mm:ss.SSS');
    % 打印当前时间，包括毫秒
    fprintf('雷达采集时间: %s\n', char(currentDateTime));

    %% 配置雷达数据采集
    addpath(genpath('.\'))
    % Initialize mmWaveStudio .NET connection
    RSTD_DLL_Path = strcat(Studio_path,'\Clients\RtttNetClientController\RtttNetClientAPI.dll');
    ErrStatus = Init_RSTD_Connection(RSTD_DLL_Path);
    if (ErrStatus ~= 30000)
        disp('Error inside Init_RSTD_Connection');
        return;
    end
    strFilename = strcat(Studio_path_2, '\\Scripts\\FrameStart.lua');
    Lua_String = sprintf('dofile("%s")',strFilename);
    ErrStatus = RtttNetClientAPI.RtttNetClient.SendCommand(Lua_String);

    %% 打印bin文件保存路径
    disp('开始采集雷达数据...');
%     Param = ParamObject();
%     pause(Param.pause_time);
    new_data_path = regexprep(data_path, '\\\\', '\');
    new_bin_name = regexprep(bin_name, '\\\\', '\');    
    fprintf('----\nbin文件保存路径:\n');
    disp(['"',new_data_path, new_bin_name,'_Raw_0.bin"']);
    fprintf('---------------------------\n\n');

end
