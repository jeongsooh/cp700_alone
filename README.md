# Update history
Flask + http api sample (home_admin_04) <==>
Adding home_admin_03
Registered user /password = admin/admin123

# How to configure the connection between charger and power meter
1. On charger
- add device with device serial number and max. current available
- set up hotspot with SSID and Password like below
2. On device: refer to WiFi connection below
WiFi connection
 SSID = gre-serialnumber (gre-300001)
 Password = "G20#RE!10sys&tem*"

# How to first-login
1. On server, run the app with python app.py
1. default account: admin/admin123 --> admin/1234
2. forgot the password? remove db.sqlite file

# How to run total system
1. run flask app CMS for web-based user interface and restful API to charging server ($ python app.py)
2. run web server for charging server ($ python ocpp_message.py)
3. run charger simulator ($ python client.py) 