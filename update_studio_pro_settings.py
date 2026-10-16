import os
import re

# 1. Update AudioEngine.settings
audio_settings_path = r'E:\Roaming\Fender\Studio Pro 8\x64\AudioEngine.settings'
if os.path.exists(audio_settings_path):
    with open(audio_settings_path, 'r', encoding='utf-8') as f:
        content = f.read()
    content = content.replace('suspendInBackground="1"', 'suspendInBackground="0"')
    with open(audio_settings_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print('Updated AudioEngine.settings: suspendInBackground=0')

# 2. Update Vstplugins.settings
vst_settings_path = r'E:\Roaming\Fender\Studio Pro 8\x64\Vstplugins.settings'
if os.path.exists(vst_settings_path):
    with open(vst_settings_path, 'r', encoding='utf-8') as f:
        content = f.read()
    content = content.replace('scanRequired="0"', 'scanRequired="1"')
    with open(vst_settings_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print('Updated Vstplugins.settings: scanRequired=1')

# 3. Clean Plugins-zh.settings: remove obsolete MiaoChang and QingXuan sections
plugins_zh_path = r'E:\Roaming\Fender\Studio Pro 8\x64\Plugins-zh.settings'
if os.path.exists(plugins_zh_path):
    with open(plugins_zh_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Split by <Section
    header = content.split('<Section ')[0]
    cleaned_sections = []
    for sec in content.split('<Section ')[1:]:
        if 'MiaoChang.vst3' in sec or 'QingXuan.vst3' in sec:
            first_line = sec.splitlines()[0]
            print('Removed section:', first_line)
            continue
        if 'Steinberg.VST3.FileList' in sec:
            lines = sec.splitlines()
            filtered_lines = [l for l in lines if 'MiaoChang' not in l and 'QingXuan' not in l]
            sec = '\n'.join(filtered_lines) + '\n'
        cleaned_sections.append(sec)

    new_content = header + '<Section ' + '<Section '.join(cleaned_sections)
    with open(plugins_zh_path, 'w', encoding='utf-8') as f:
        f.write(new_content)
    print('Cleaned Plugins-zh.settings successfully')
