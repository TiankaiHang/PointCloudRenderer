import os
import sys
import imageio
import numpy as np
import platform
from multiprocessing import Pool

imageio.plugins.freeimage.download()


def get_platform():
    return platform.system().lower()


## ref: https://stackoverflow.com/questions/50748084/convert-exr-to-jpeg-using-imageio-and-python
# def convert_exr_to_jpg(exr_file, jpg_file):
#     if not os.path.isfile(exr_file):
#         return False

#     filename, extension = os.path.splitext(exr_file)
#     if not extension.lower().endswith('.exr'):
#         return False

#     # imageio.plugins.freeimage.download() #DOWNLOAD IT
#     image = imageio.imread(exr_file, format='EXR-FI')

#     # remove alpha channel for jpg conversion
#     image = image[:,:,:3]

#     # normalize the image
#     data = image.astype(image.dtype) / image.max() # normalize the data to 0 - 1
#     data = 255 * data # Now scale by 255
#     rgb_image = data.astype('uint8')
#     # rgb_image = imageio.core.image_as_uint(rgb_image, bitdepth=8)

#     imageio.imwrite(jpg_file, rgb_image)
#     return True


def convert_exr_to_jpg(exr_file, jpg_file):
    if not os.path.isfile(exr_file):
        return False

    _, extension = os.path.splitext(exr_file)
    if not extension.lower().endswith('.exr'):
        return False

    # imageio.plugins.freeimage.download() #DOWNLOAD IT
    image = imageio.imread(exr_file)

    # remove alpha channel for jpg conversion
    image = image[:,:,:3]

    data = 65535 * image + 15000
    data[data > 65535] = 65535
    rgb_image = data.astype('uint16')
    print(rgb_image.dtype)
    rgb_image = imageio.core.image_as_uint(rgb_image, bitdepth=16)

    imageio.imwrite(jpg_file, rgb_image)
    return True


def standardize_bbox(pcl, points_per_object=-1):
    points_per_object = min(pcl.shape[0], points_per_object) \
        if points_per_object > 0 else pcl.shape[0]
    
    pt_indices = np.random.choice(pcl.shape[0], points_per_object, replace=False)
    np.random.shuffle(pt_indices)
    pcl = pcl[pt_indices] # n by 3
    mins = np.amin(pcl, axis=0)
    maxs = np.amax(pcl, axis=0)
    center = ( mins + maxs ) / 2.
    scale = np.amax(maxs - mins)
    print("Center: {}, Scale: {}".format(center, scale))
    result = ((pcl - center) / scale).astype(np.float32) * 2.0 # [-1.0, 1.0]
    return result


xml_head = \
"""
<scene version="0.6.0">
    <integrator type="path">
        <integer name="maxDepth" value="-1"/>
    </integrator>
    <sensor type="perspective">
        <float name="farClip" value="100"/>
        <float name="nearClip" value="0.1"/>
        <transform name="toWorld">
            <lookat origin="3,3,3" target="0,0,0" up="0,0,1"/>
        </transform>
        <float name="fov" value="25"/>
        <sampler type="independent">
            <integer name="sampleCount" value="256"/>
        </sampler>
        <film type="hdrfilm">
            <integer name="width" value="1200"/>
            <integer name="height" value="1200"/>
            <rfilter type="gaussian"/>
            <boolean name="banner" value="false"/>
        </film>
    </sensor>
    
    <bsdf type="roughplastic" id="surfaceMaterial">
        <string name="distribution" value="ggx"/>
        <float name="alpha" value="0.05"/>
        <float name="intIOR" value="1.46"/>
        <rgb name="diffuseReflectance" value="1,1,1"/> <!-- default 0.5 -->
    </bsdf>
"""


xml_ball_segment = \
"""
    <shape type="sphere">
        <float name="radius" value="0.025"/>
        <transform name="toWorld">
            <translate x="{}" y="{}" z="{}"/>
        </transform>
        <bsdf type="diffuse">
            <rgb name="reflectance" value="{},{},{}"/>
        </bsdf>
    </shape>
"""


xml_tail = \
"""
    <shape type="rectangle">
        <ref name="bsdf" id="surfaceMaterial"/>
        <transform name="toWorld">
            <scale x="10" y="10" z="1"/>
            <translate x="0" y="0" z="-0.5"/>
        </transform>
    </shape>
    
    <shape type="rectangle">
        <transform name="toWorld">
            <scale x="10" y="10" z="1"/>
            <lookat origin="-4,4,20" target="0,0,0" up="0,0,1"/>
        </transform>
        <emitter type="area">
            <rgb name="radiance" value="6,6,6"/>
        </emitter>
    </shape>
</scene>
"""


def colormap(x, y, z):
    vec = np.array([x, y, z])
    vec = np.clip(vec, 0.001, 1.0)
    norm = np.sqrt(np.sum(vec ** 2))
    vec /= norm
    return [vec[0], vec[1], vec[2]]


def main_worker(fn, manual_color=None, num_points=-1):
    xml_segments = [xml_head]
    basename = os.path.basename(fn).split('.')[0]
    pcl = np.load(fn)
    if pcl.shape[1] == 6:
        pcl, colors = pcl[:, :3], pcl[:, 3:]
    pcl = standardize_bbox(pcl, num_points)
    print(f"Render point cloud with shape {pcl.shape}")
    pcl = pcl[:, [2, 0, 1]]
    pcl[:, 0] *= -1
    pcl[:, 2] += 0.0125
    for i in range(pcl.shape[0]):
        delta = 0.5
        if pcl.shape[1] == 6:
            color = [colors[i][0], colors[i][1], colors[i][2]]
        elif manual_color is None:
            color = colormap(pcl[i, 0]+delta, pcl[i, 1]+delta, pcl[i, 2]+delta-0.0125)
        else:
            color = manual_color
        xml_segments.append(
            xml_ball_segment.format(pcl[i, 0], pcl[i, 1], pcl[i, 2], *color))
    xml_segments.append(xml_tail)
    xml_content = str.join('', xml_segments)
    with open(f'{basename}.xml', 'w') as f:
        f.write(xml_content)
    # render xml to exr
    os.system(f"mitsuba {basename}.xml")
    # change exr to jpeg
    convert_exr_to_jpg(
        f'{basename}.exr', 
        os.path.join(out_path, f'{basename}.png'))


if __name__ == '__main__':

    data_path = sys.argv[1]
    out_path = sys.argv[2]

    os.makedirs(out_path, exist_ok=True)

    files = []
    if os.path.isfile(data_path):
        files.append(data_path)

    elif os.path.isdir(data_path):
        for _f in os.listdir(data_path):
            files.append(
                os.path.join(data_path, _f))

    files = [_f for _f in files if _f.endswith('.npy')]

    # multi-processing
    # p = Pool(processes=1)
    
    for _f in files:
        # p.apply_async(main_worker, args=(_f, ))
        main_worker(_f, manual_color=[0.4, 0.6, 0.8], num_points=4096)
        
    # p.close()
    # p.join()
    
    _platform = get_platform()
    if _platform == 'linux':
        os.system(f'rm *.xml')
        os.system(f'rm *.exr')
    elif _platform == 'windows':
        os.system(f'del *.xml')
        os.system(f'del *.exr')
    else:
        raise ValueError(f'Such platform {_platform} is not supported')