from flask import Flask, jsonify, request

app = Flask(__name__)
system_settings = {"IndicatorLED": "Off"}

@app.route('/redfish/v1')
def redfish_root():
    return jsonify({
        "@odata.id": "/redfish/v1",
        "@odata.type": "#ServiceRoot.v1_0_0.ServiceRoot",
        "Id": "RootService",
        "Name": "Root Service",
        "RedfishVersion": "1.0.0",
        "UUID": "00000000-0000-0000-0000-000000000000",
        "Systems": {
            "@odata.id": "/redfish/v1/Systems"
        },
        "Chassis": {
            "@odata.id": "/redfish/v1/Chassis"
        },
        "Managers": {
            "@odata.id": "/redfish/v1/Managers"
        }
    })

@app.route('/redfish/v1/Systems')
def systems():
    return jsonify({
        "@odata.id": "/redfish/v1/Systems",
        "@odata.type": "#ComputerSystemCollection.ComputerSystemCollection",
        "Name": "Computer System Collection",
        "Members@odata.count": 1,
        "Members": [
            {
                "@odata.id": "/redfish/v1/Systems/1"
            }
        ]
    })

@app.route('/redfish/v1/Systems/1')
def system1():
    response = jsonify({
        "@odata.id": "/redfish/v1/Systems/1",
        "@odata.type": "#ComputerSystem.v1_0_0.ComputerSystem",
        "@odata.etag": '"system-1"',
        "Id": "1",
        "Name": "Computer System",
        "SystemType": "Physical",
        "IndicatorLED": system_settings["IndicatorLED"],
        "IndicatorLED@Redfish.AllowableValues": ["Off", "Lit", "Blinking"],
        "@Redfish.Settings": {
            "SettingsObject": {
                "@odata.id": "/redfish/v1/Systems/1/Settings"
            },
            "SupportedApplyTimes": ["Immediate", "OnReset"]
        },
        "Actions": {
            "#ComputerSystem.Reset": {
                "target": "/redfish/v1/Systems/1/Actions/ComputerSystem.Reset",
                "@Redfish.ActionInfo": "/redfish/v1/Systems/1/ResetActionInfo"
            }
        },
        "Status": {
            "State": "Enabled",
            "Health": "OK"
        }
    })
    response.headers["ETag"] = '"system-1"'
    response.headers["Allow"] = "GET, PATCH"
    return response


@app.route('/redfish/v1/Systems/1/Settings', methods=['GET', 'PATCH'])
def system1_settings():
    if request.method == 'PATCH':
        allowed = {"IndicatorLED", "@Redfish.SettingsApplyTime"}
        if not set(request.json or {}).issubset(allowed):
            return jsonify({"error": {"message": "Read-only property"}}), 400
        if "IndicatorLED" in request.json:
            system_settings["IndicatorLED"] = request.json["IndicatorLED"]
        return "", 204
    response = jsonify({
        "@odata.id": "/redfish/v1/Systems/1/Settings",
        "@odata.type": "#ComputerSystem.v1_0_0.ComputerSystem",
        "@odata.etag": '"settings-1"',
        "Id": "1",
        "Name": "Pending Computer System Settings",
        "IndicatorLED": system_settings["IndicatorLED"],
        "IndicatorLED@Redfish.AllowableValues": ["Off", "Lit", "Blinking"],
        "Status": {"State": "Enabled"}
    })
    response.headers["ETag"] = '"settings-1"'
    response.headers["Allow"] = "GET, PATCH"
    return response


@app.route('/redfish/v1/Systems/1/ResetActionInfo')
def reset_action_info():
    return jsonify({
        "@odata.id": "/redfish/v1/Systems/1/ResetActionInfo",
        "@odata.type": "#ActionInfo.v1_0_0.ActionInfo",
        "Id": "ResetActionInfo",
        "Name": "Reset Action Info",
        "Parameters": [{
            "Name": "ResetType",
            "Required": True,
            "DataType": "String",
            "AllowableValues": ["GracefulRestart", "ForceRestart"]
        }]
    })


@app.route(
    '/redfish/v1/Systems/1/Actions/ComputerSystem.Reset',
    methods=['POST']
)
def reset_system():
    if (request.json or {}).get("ResetType") not in (
        "GracefulRestart", "ForceRestart"
    ):
        return jsonify({"error": {"message": "Invalid ResetType"}}), 400
    return "", 204

@app.route('/redfish/v1/Chassis')
def chassis():
    return jsonify({
        "@odata.id": "/redfish/v1/Chassis",
        "@odata.type": "#ChassisCollection.ChassisCollection",
        "Name": "Chassis Collection",
        "Members@odata.count": 1,
        "Members": [
            {
                "@odata.id": "/redfish/v1/Chassis/1"
            }
        ]
    })

@app.route('/redfish/v1/Chassis/1')
def chassis1():
    return jsonify({
        "@odata.id": "/redfish/v1/Chassis/1",
        "@odata.type": "#Chassis.v1_0_0.Chassis",
        "Id": "1",
        "Name": "Chassis",
        "ChassisType": "RackMount",
        "Status": {
            "State": "Enabled",
            "Health": "OK"
        }
    })

@app.route('/redfish/v1/Managers')
def managers():
    return jsonify({
        "@odata.id": "/redfish/v1/Managers",
        "@odata.type": "#ManagerCollection.ManagerCollection",
        "Name": "Manager Collection",
        "Members@odata.count": 1,
        "Members": [
            {
                "@odata.id": "/redfish/v1/Managers/1"
            }
        ]
    })

@app.route('/redfish/v1/Managers/1')
def manager1():
    return jsonify({
        "@odata.id": "/redfish/v1/Managers/1",
        "@odata.type": "#Manager.v1_0_0.Manager",
        "Id": "1",
        "Name": "Manager",
        "ManagerType": "BMC",
        "FirmwareVersion": "1.0.0",
        "Status": {
            "State": "Enabled",
            "Health": "OK"
        }
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=True)