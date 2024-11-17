pymobiledevice3 usbmux list

pymobiledevice3 mounter auto-mount

# 터널링 시작 (유선)
sudo python3 -m pymobiledevice3 remote tunneld

# 터널링 시작 (WiFi)
sudo python3 -m pymobiledevice3 remote start-tunnel -t wifi

pymobiledevice3 developer dvt simulate-location play test.gpx
