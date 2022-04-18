from recorder.device import Device

import pyrealsense2 as rs


class RealSense(Device):

    def __init__(self, *args, streams: dict, serial_number: str, **kwargs):
        super().__init__(*args, **kwargs)
        self.streams = streams
        self.serial_number = serial_number

    @classmethod
    def find(cls) -> dict:
        devices = {}
        for d in rs.context().query_devices():
            sn = d.get_info(rs.camera_info.serial_number)
            config = rs.config()
            config.enable_device(sn)
            config.enable_all_streams()
            pipeline_profile = config.resolve(
                rs.pipeline_wrapper(rs.pipeline())
                )
            streams = {}
            for s in pipeline_profile.get_streams():
                name = s.stream_name()
                streams[name] = {
                    'format': str(s.format())[7:],  # remove 'format.'
                    'framerate': s.fps(),
                    'type': str(s.stream_type())[7:],  # remove 'stream.'
                    }
                if s.is_motion_stream_profile():
                    streams[name]['intrinsics'] = \
                        s.as_motion_stream_profile().get_motion_intrinsics().data
                elif s.is_video_stream_profile():
                    intrinsics = s.as_video_stream_profile().get_intrinsics()
                    streams[name].update({
                        'coeffs': intrinsics.coeffs,
                        'model': str(intrinsics.model)
                                 [11:],  # remove 'distortion.'
                        'fx': intrinsics.fx,
                        'fy': intrinsics.fy,
                        'width': intrinsics.width,
                        'height': intrinsics.height,
                        'ppx': intrinsics.ppx,
                        'ppy': intrinsics.ppy,
                        })
            devices[sn] = {
                'name': d.get_info(rs.camera_info.name),
                'streams': streams,
                'serial_number': sn,
                }
        return devices


# RealSense = Device(find_realsense, 'RealSense')
# RealSense.config_map = {
#     'streams': 'streams',
#     **RealSense.config_map,
#     }