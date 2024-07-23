from math import pi, sin, cos, atan2
from direct.showbase.ShowBase import ShowBase
from direct.showbase.DirectObject import DirectObject
from direct.task import Task
from direct.actor.Actor import Actor
from direct.interval.IntervalGlobal import Sequence
from panda3d.core import Point3, InputDevice, CardMaker, TextureStage, AmbientLight, DirectionalLight, Vec4, Vec3, AntialiasAttrib, PandaNode, Spotlight
from direct.task import Task

import can
import cantools

import time
import csv

def read_cones():
    CONES_CSV = './hockenheim_cones.csv'
    cones_pos_1 = []
    cones_pos_2 = []
    with open(CONES_CSV) as f:
        for row in csv.reader(f, csv.excel_tab):
            cones_pos_1.append(tuple(map(float, row[0:2])))
            cones_pos_2.append(tuple(map(float, row[2:4])))
    return cones_pos_1, cones_pos_2


#class MyApp(ShowBase):
class MyApp(DirectObject):
    def __init__(self):
        #ShowBase.__init__(self)
        self.bus = can.Bus("vcanv", interface="socketcan")

        canv_dbc_path = 'can_common/dbc/can_v.dbc'
        self.can_v_db = cantools.database.load_file(canv_dbc_path)
        self.simulator_pos_msg = self.can_v_db.get_message_by_name(
            "SIMULATOR_SimulatorPos"
        )
        self.bus.set_filters([{"can_id": self.simulator_pos_msg.frame_id, "can_mask": 0x7FF, "extended": False}])

        base.disableMouse()
        self.terrain = loader.loadTexture("road_texture.jpg")
        cm = CardMaker("terrain")
        cm.setFrame(-2, 2, -2, 2)
        floor = render.attachNewNode(PandaNode("floor"))
        for y in range(12):
            for x in range(12):
                nn = floor.attachNewNode(cm.generate())
                nn.setP(-90)
                nn.setPos((x - 6) * 4, (y - 6) * 4, 0)

        floor.setTexture(self.terrain)
        #floor.setHpr(0, -90, 0)
        floor.setScale(100)
        floor.flattenStrong()

        cone = loader.loadModel("300mm blue road cone.STL")
        cone.setTwoSided(True)
        cone.setScale(0.0010, 0.0010, 0.0010)
        cone.setColor(1,0.5,0.0,1)
        cone.setHpr(0, 90, 0)


        cones_side_1, cones_side_2 = read_cones()
        for c in cones_side_1 + cones_side_2:
            cone_instance = cone.copyTo(render)
            cone_instance.setPos(*c, 0)
            cone_instance.setShaderAuto()

        # Aggiunta di una luce ambientale
        ambientLight = AmbientLight("ambientLight")
        ambientLight.setColor(Vec4(0.2, 0.2, 0.2, 1))
        render.setLight(render.attachNewNode(ambientLight))
        
        # Aggiunta di una luce direzionale
        directionalLight = DirectionalLight("directionalLight")
        directionalLight.setDirection(Vec3(1, -1, -1))
        directionalLight.setColorTemperature(6000)
        directionalLight.color = directionalLight.color * 0.4
        directionalLight.setShadowCaster(True)
        directionalLight.getLens().setNearFar(1, 30)
        directionalLight.getLens().setFilmSize(20, 40)

        dlpath = render.attachNewNode(directionalLight)
        dlpath.setPos(10, 10, 10)

        render.setLight(dlpath)

        #self.spotlight = render.attachNewNode(Spotlight("Spotlight"))
        #self.spotlight.node().setScene(render)
        #self.spotlight.node().setShadowCaster(True)
        #self.spotlight.node().getLens().setFov(40)
        #self.spotlight.node().getLens().setNearFar(10, 100)
        #self.spotlight.setPos(0, 30, 10)
        #render.setLight(self.spotlight)

        render.setShaderAuto(True)
        render.setAntialias(AntialiasAttrib.MAuto)

        self.start_pos_x = (cones_side_1[0][0] + cones_side_2[0][0])/2
        self.start_pos_y = (cones_side_1[0][1] + cones_side_2[0][1])/2

        lookat_pos_x = (cones_side_1[1][0] + cones_side_2[1][0])/2
        lookat_pos_y = (cones_side_1[1][1] + cones_side_2[1][1])/2
        #self.start_angle = atan2(lookat_pos_y - self.start_pos_y, lookat_pos_x - self.start_pos_x)

        camera.setPos(self.start_pos_x, self.start_pos_y, 0.5)
        camera.lookAt(lookat_pos_x, lookat_pos_y, 0.3)
        self.start_angle = camera.getH()

        self.can_task = taskMgr.add(self.handle_can, "handle_can")

    def handle_can(self, task):
        msg = self.bus.recv(0)
        if msg is not None and msg.arbitration_id == self.simulator_pos_msg.frame_id:
            data = self.simulator_pos_msg.decode(msg.data)
            camera.setPos(self.start_pos_x + data['x'], self.start_pos_y + data['y'], 0.5)
            angle = (self.start_angle + data['theta'] * 180/pi + 180) % 360
            camera.setH(angle)

        return Task.cont


base = ShowBase()
a = MyApp()
base.run()
