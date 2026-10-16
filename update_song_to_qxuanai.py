import os
import shutil
import zipfile

song_path = r'C:/Users/Administrator/Documents/Studio Pro/Songs/妙唱/妙唱.song'
bak_path = r'C:/Users/Administrator/Documents/Studio Pro/Songs/妙唱/妙唱.song.bak_miaochang'

if os.path.exists(song_path):
    if not os.path.exists(bak_path):
        shutil.copy2(song_path, bak_path)
        print('Created backup:', bak_path)

    # Read all entries and transform
    entries = {}
    with zipfile.ZipFile(song_path, 'r') as zin:
        for item in zin.infolist():
            data = zin.read(item.filename)
            new_name = item.filename.replace('MiaoChang', 'QXuanAI')
            if item.filename == 'Devices/audiomixer.xml':
                data = data.replace(b'name="MiaoChang"', b'name="QXuanAI"')
                data = data.replace(b'1 - MiaoChang.vstpreset', b'1 - QXuanAI.vstpreset')
                print('Replaced MiaoChang with QXuanAI in Devices/audiomixer.xml')
            entries[new_name] = data

    # Write back to song_path
    tmp_path = song_path + '.tmp'
    with zipfile.ZipFile(tmp_path, 'w', compression=zipfile.ZIP_DEFLATED) as zout:
        for name, data in entries.items():
            zout.writestr(name, data)

    shutil.move(tmp_path, song_path)
    print('Updated song file successfully with QXuanAI!')
