from flask import Flask, jsonify, request

app = Flask(__name__)

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

@app.route('/redfish/v1/Systems/1', methods=['GET', 'PATCH'])
def system1():
    if request.method == 'PATCH':
        # Simple mock: accept any patch and return success
        return '', 204
    return jsonify({
        "@odata.id": "/redfish/v1/Systems/1",
        "@odata.type": "#ComputerSystem.v1_0_0.ComputerSystem",
        "Id": "1",
        "Name": "Computer System",
        "SystemType": "Physical",
        "Status": {
            "State": "Enabled",
            "Health": "OK"
        }
    })

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
        "Status": {
            "State": "Enabled",
            "Health": "OK"
        }
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=True)