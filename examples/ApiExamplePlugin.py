# MIKAIA SlideService test script
import os
import sys
from mikaia_plugin_api import mikaia_api

def nextStep(ss, progress_0to1, msg, allowSkip = True):
    text = 'Next step: ' + msg
    if ss is not None:
        ss.sendProgress(progress_0to1, 0, text)
    print()
    print('#####################################################################')
    print('Next step: ' + msg)
    if allowSkip:
        text = input('Press [Enter] to continue([x][Enter] to skip step):')
        if text == 'x':
            print('Step skipped !')
            if ss is not None:
                ss.sendProgress(progress_0to1, 0, 'Step skipped !')
    else:
        text = input('Press [Enter] to continue:')
    print()
    return (allowSkip == False or text != 'x')
    
def showReceivedImage(img):
    if img is not None:
        img.show();

# normalized width(0.0 to 1.0) to width in slide coordinate units(um)
def nw2um(si, normalized_width):
    return si.slideRect.width * normalized_width

# normalized height(0.0 to 1.0) to height in slide coordinate units(um)
def nh2um(si, normalized_height):
    return si.slideRect.height * normalized_height

# point in normalized coordinates(0.0 to 1.0) to point in slide coordinates(um)
def np2um(si, normalized_point):
    x_um = si.slideRect.x + (normalized_point[0] * si.slideRect.width)
    y_um = si.slideRect.y + (normalized_point[1] * si.slideRect.height)
    return [x_um, y_um]

# array of points in normalized coordinates(0.0 to 1.0) to array of points in slide coordinates(um)
def npa2um(si, normalized_point_array):
    point_array_um = []
    for pt in normalized_point_array:
        point_array_um.append(np2um(si, pt))
    return point_array_um

# transform(scale and translate) array of normalized coordinates(0.0 to 1.0)
def npa_transform(normalized_point_array, offset_x, offset_y, scale_x, scale_y):
    transformed_array = []
    for pt in normalized_point_array:
        transformed_array.append([(pt[0]*scale_x) + offset_x, (pt[1]*scale_y) + offset_y])
    return transformed_array

# create a face graphic as 'PathWithHoles' annotation
def create_face_anno(ss, si, offset_x, offset_y, scale_x, scale_y):
    face_outline = [[0.0, 0.0], [1.0, 0.0], [0.9, 1.0], [0.1, 1.0]]
    left_eye = [[0.15, 0.12], [0.27, 0.12], [0.27, 0.24], [0.15, 0.24]]
    right_eye = [[0.73, 0.12], [0.85, 0.12], [0.85, 0.24], [0.73, 0.24]]
    nose = [[0.5, 0.18], [0.58, 0.43], [0.42, 0.43]]
    mouth = [[0.2, 0.55], [0.85, 0.55], [0.75, 0.85], [0.60, 0.90], [0.45, 0.90], [0.30, 0.85]]
    
    outline = npa2um(si, npa_transform(face_outline, offset_x, offset_y, scale_x, scale_y))
    holes = [npa2um(si, npa_transform(left_eye, offset_x, offset_y, scale_x, scale_y))]
    holes.append(npa2um(si, npa_transform(right_eye, offset_x, offset_y, scale_x, scale_y)))
    holes.append(npa2um(si, npa_transform(nose, offset_x, offset_y, scale_x, scale_y)))
    holes.append(npa2um(si, npa_transform(mouth, offset_x, offset_y, scale_x, scale_y)))
    
    return ss.createAnnotation('PathWithHoles', outline, holes, 'Face')

def main():
    # Display passed arguments:
    print("####################")
    print("Passed arguments:")
    for eachArg in sys.argv:   
        print(eachArg)
    print("####################")
    print()

    # The SlideService root path shall be passed as first argument
    slideServicePath = sys.argv[1]
    print(f'MIKAIA SlideService root path: "{slideServicePath}"')
    
    ##########################
    # Create interface object to access MIKAIA SlideService
    ##########################
    if nextStep(None, 0.05, 'Create SlideService interface object "ss" to access MIKAIA SlideService', False):
        ss = mikaia_api.SlideService(slideServicePath)
        print(f'ss:\r\n{ss}')

    ##########################
    # Request slide info and user parameters from MIKAIA SlideService
    ##########################
    if nextStep(ss, 0.10, "Request slide infos and user parameters"):
        slideInfo = ss.getSlideInfo()
        userParam = ss.getUserParameters()
        print(slideInfo)
        if len(userParam) > 0:
            print('User parameters: {}'.format(userParam))
        else:
            print('No user parameters available')
        
         
    ##########################
    # Request thumbnail image from MIKAIA SlideService
    ##########################
    if nextStep(ss, 0.15, "Request thumbnail image"):
        thumbnail = ss.getThumbnail(800, 600, False)
        showReceivedImage(thumbnail)

    ##########################
    # Request a ROI(with 4.0 um pixel resolution) from MIKAIA SlideService
    ##########################
    if nextStep(ss, 0.20, "Request a ROI(with 4.0 um pixel resolution)"):
        TL_um = np2um(slideInfo, [0.2, 0.4])
        w_um = nw2um(slideInfo, 0.2)
        h_um = nh2um(slideInfo, 0.15)
        roi = ss.getROI(TL_um[0], TL_um[1], w_um, h_um, 4.0, 4.0, 'RGB', -1, False)
        showReceivedImage(roi)

    ##########################
    # Request a ROI(with 4.0 um pixel resolution) as grayscale image from MIKAIA SlideService
    ##########################
    if nextStep(ss, 0.25, "Request a ROI(with 4.0 um pixel resolution) as grayscale image"):
        roi = ss.getROI(TL_um[0], TL_um[1], w_um, h_um, 4.0, 4.0, 'Gray', -1, False)
        showReceivedImage(roi)

    ##########################
    # Request a 1200x1000 pixel ROI with native pixel resolution from MIKAIA SlideService
    ##########################
    if nextStep(ss, 0.30, "Request a 1200x1000 pixel ROI with native pixel resolution"):
        TL_um = np2um(slideInfo, [0.2, 0.45])
        nativeROI = ss.getNativeROI(TL_um[0], TL_um[1], 1200, 1000, 'RGB', -1, False)
        showReceivedImage(nativeROI)

    ##########################
    # Add annotation classes with different style properties to MIKAIA SlideService
    ##########################
    annoClass0 = ss.createAnnotationClass('Unclassified', 'Unclassified annotations', 2, '#ff909090')
    annoClass1 = ss.createAnnotationClass('Class One', 'Annotations of class One', 5, '#FFAABB00')
    annoClass2 = ss.createAnnotationClass('Class Two', 'Annotations of class Two', 3, '#ff009080', '#ff00bbaa', 0.5 )
    annoClassFace = ss.createAnnotationClass('Face', 'Face annotations', 3, '#ff900070', '#ffbb00aa', 0.6 )
    if nextStep(ss, 0.35, "Add annotation classes with different style properties"):
        ss.addAnnotationClasses([annoClass0, annoClass1, annoClass2, annoClassFace])

    ##########################
    # Add annotations to MIKAIA SlideService
    ##########################
    shape_points_um = npa2um(slideInfo, [[0.05, 0.1], [0.3, 0.225]])
    rect_anno = ss.createAnnotation('Rectangle', shape_points_um)
    rect_anno.className = 'Unclassified'
    shape_points_um = npa2um(slideInfo, [[0.05, 0.5], [0.3, 0.72]])
    ellipse_anno = ss.createAnnotation('Ellipse', shape_points_um)
    ellipse_anno.className = 'Unclassified'
    if nextStep(ss, 0.40, "Add a rectangle and an ellipse annotation(class name: 'Unclassified')"):
        ss.addAnnotations([rect_anno, ellipse_anno])
        print(rect_anno)
        print(ellipse_anno)

    shape_points_um = npa2um(slideInfo, [[0.5, 0.25], [0.6, 0.15], [0.75, 0.425], [0.65, 0.275], [0.52, 0.35], [0.5, 0.25]])
    poly_anno = ss.createAnnotation('Polygon', shape_points_um)
    poly_anno.className = 'Class One'
    if nextStep(ss, 0.45, "Add a polygon annotation(class name: 'Class One')"):
        ss.addAnnotations([poly_anno])
        print(poly_anno)
        
    shape_points_um = npa2um(slideInfo, [[0.45, 0.55], [0.67, 0.775]])
    rect_anno2 = ss.createAnnotation('Rectangle', shape_points_um)
    rect_anno2.className = 'Class Two'
    if nextStep(ss, 0.50, "Add a rectangle annotation(class name: 'Class Two')"):
        ss.addAnnotations([rect_anno2])
        print(rect_anno2)

    face_annos = [create_face_anno(ss, slideInfo, 0.1, 0.25, 0.2, 0.2)]
    face_annos.append(create_face_anno(ss, slideInfo, 0.5, 0.40, 0.1, 0.1))
    face_annos.append(create_face_anno(ss, slideInfo, 0.7, 0.60, 0.25, 0.35))
    if nextStep(ss, 0.55, "Add 3 'PathWithHoles' annotations(class name: 'Face')"):
        ss.addAnnotations(face_annos)
        print('Added {} "PathWithHoles" annotations'.format(len(face_annos)))

    ##########################
    # Request annotations from MIKAIA SlideService
    ##########################
    if nextStep(ss, 0.60, "Request annotation items"):
        anno_list = ss.getAnnotations()
        print(f"{len(anno_list)} annotations received:")
        for item in anno_list:
            print(item)

    ##########################
    # Change class of 'Unclassified' rectangle annotation to 'ClassOne'
    ##########################
    if nextStep(ss, 0.65, "Change class of 'Unclassified' rectangle annotation to 'Class One'"):
        rect_anno.className = 'Class One'
        ss.updateAnnotation(rect_anno)

    ##########################
    # Request all annotations of class 'ClassOne' from MIKAIA SlideService
    ##########################
    if nextStep(ss, 0.70, "Request all annotations of class 'Class One'"):
        anno_list = ss.getAnnotations('', 'Class One')
        print(f"{len(anno_list)} annotations received:")
        for item in anno_list:
            print(item)

    ##########################
    # Request all annotations of type 'Rectangle' from MIKAIA SlideService
    ##########################
    if nextStep(ss, 0.75, "Request all annotations of type 'Rectangle'"):
        anno_list = ss.getAnnotations('Rectangle')
        print(f"{len(anno_list)} annotations received:")
        for item in anno_list:
            print(item)

    ##########################
    # Request all rectangle annotations of class 'ClassOne' from MIKAIA SlideService
    ##########################
    if nextStep(ss, 0.80, "Request all 'Rectangle' annotations of class 'Class One'"):
        anno_list = ss.getAnnotations('Rectangle', 'Class One')
        print(f"{len(anno_list)} annotations received:")
        for item in anno_list:
            print(item)

    ##########################
    # Change class of 'Unclassified' ellipse annotation to class 'ClassThree'
    ##########################
    if nextStep(ss, 0.85, "Change class of 'Unclassified' ellipse annotation to class 'Class Three'"):
        ellipse_anno.className = 'Class Three'
        ss.updateAnnotation(ellipse_anno)

    ##########################
    # Request annotation classes from MIKAIA SlideService
    ##########################
    if nextStep(ss, 0.90, "Request annotation classes"):
        anno_class_list = ss.getAnnotationClasses()
        print(f"{len(anno_class_list)} annotation classes received:")
        for item in anno_class_list:
            print(item)

    ##########################
    # Change style properties(line width and color) of class 'Class One' and class 'Face'
    ##########################
    if nextStep(ss, 0.95, "Change style properties(line width and color) of class 'Class One' and class 'Face'"):
        annoClass1.outlineWidth = 3
        annoClass1.outlineColor = '#ffaa00bb'
        ss.updateAnnotationClass(annoClass1)
        annoClassFace.fillColor = '#fff0e000'
        ss.updateAnnotationClass(annoClassFace)
        
    ss.sendProgress(1.0, 0, "All tests done.")
    print()
    print()
    input("All tests done - Press [Enter] to exit the script:")


if __name__ == '__main__':
    main()