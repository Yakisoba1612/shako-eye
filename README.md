# shako-eye
シャコの眼を人間の視覚に落とし込みます。あと色々。

LLMを使用しています。人が書いているのはREADMEくらいです。

Githubへの投稿はこれが初めてです。
ひとまず何も見ずに我流でREADMEも書いています。
落ち着いたら直します。

対応確認環境
・python 3.11
・Windows10

推奨環境
・サポート対応CUDA搭載GPU
・4スレッド以上のCPU
・RAM 16GB以上

開発環境
・Athlon 200GE
・GeoForce GT740
・DDR4 2666MHz 32GB
・NVMe SSD 1TB
自分のがサポート中のCUDA非搭載なので細かくは不明ですが、新しめのCUDAがあると処理が早くなります。たぶん。
最適化はしていないのでメモリは多いほどいいです。キャッシュを使うのでストレージも読み書きが速いほどいいです。

使い方
lancher.batから起動します。
ブラウザが起動します。
RAW画像を用意してください。
サンプルのRAW画像はサイズ制限に引っかかるのでアップロードしていません。

各種ファイル
main.py：透過率を設定したフィルターを人が見た時の景色が見えます。
color.py：csvファイルから波長ごとに色を表示します。csvファイルはまだありません。
approximator.py：main.pyで用いるパラメータをcsvから近似算出します。
koujo.py：色恒常性に関するもの。人に見分けられずシャコに見分けられる反射スペクトルというものを再現しています。Information processing by the 20-channel mantis shrimp visual system 参照
doga.py：RAW動画から物理的なエネルギーに基づき白黒動画を合成します。
toDNG.py：jpegなどを無理やりDNG形式に変換します。

提携
https://www.youtube.com/channel/UCrtrk6CgIU3nghgEyIXbYGA
