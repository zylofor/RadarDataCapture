function RadarConfigure
    %% 本文件用于 通过lua脚本，向mmwave studio发送雷达的配置参数  
	%% 打开studio并等待FTDI显示connected后即可运行该文件
    fprintf('\n----------RadarConfig-----------\n');
    addpath(genpath('.\'))
    RSTD_DLL_Path = 'E:\\ti\mmwave_studio_02_01_01_00\\mmWaveStudio\\Clients\\RtttNetClientController\\RtttNetClientAPI.dll';
    ErrStatus = Init_RSTD_Connection(RSTD_DLL_Path); 
    if (ErrStatus ~= 30000)
        disp('Error inside Init_RSTD_Connection');
        return;
    end
    % lua脚本文件地址，雷达参数配置在该lua脚本
	strFilename='E:\\ti\\mmwave_studio_02_01_01_00\\mmWaveStudio\\Scripts\\DataCaptureDemo_6843_UAV.lua'; 
    Lua_String = sprintf('dofile("%s")',strFilename);
    ErrStatus = RtttNetClientAPI.RtttNetClient.SendCommand(Lua_String);

end