from recorder.device import Device

import pyrealsense2 as rs


class RealSense(Device):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not (streams := self.config.get('streams', [])):
            raise AttributeError('No `streams` found in device')
        assert 'serial_number' in self.config
        sn = self.config['serial_number']
        self.rsconfig = rs.config()
        self.rsconfig.enable_device(sn)
        for stream in streams.values():
            parameters = {
                'stream_type': getattr(rs.stream, stream['type']),
                'format': getattr(rs.format, stream['format']),
                'framerate': stream['framerate'],
                }
            if 'width' in stream:
                parameters['width'] = stream['width']
                parameters['height'] = stream['height']
            self.rsconfig.enable_stream(**parameters)
        self.rsconfig.enable_record_to_file(
            str(self.output_file.with_suffix('.bag'))
            )
        self.pipeline = rs.pipeline()

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

    def _start(self):
        self.pipeline.start(self.rsconfig)
    
    def _stop(self):
        self.pipeline.stop()

    @classmethod
    def show_results(cls, from_folder):
        for _file in from_folder.glob(f'{repr(cls)}*.bag'):
            print(f'{_file}: {_file.stat().st_size} bytes')
            with open(_file.with_suffix('.yaml'), encoding='utf-8') as f:
                print(f.read())