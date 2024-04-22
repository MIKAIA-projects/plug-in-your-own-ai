import tensorflow as tf
import numpy as np
import sys
from mikaia_plugin_api import mikaia_api

def main():
    
    # the MIKAIA Script Service will pass MIKAIA's SlideService URL + Session ID as the 1st argument.

    # to attach a debugger, you can start the "MIKAIA Python Console" in MIKAIA, 
    # and then copy the URL and pass it as an argument when you launch this script. 
    #
    #  A Visual Studio Code launch.json for Windows could look like this:
    #{
    #    "version": "0.2.0",
    #    "configurations": [
    #        {
    #            "name": "Python: Current File",
    #            "type": "python",
    #            "python": "C:/MIKAIA-Python-Plugin-env/Scripts/python.exe",
    #            "request": "launch",
    #            "program": "${file}",
    #            "console": "integratedTerminal",
    #            "args" : ["http://10.54.75.161:9980/MIKAIA/SlideService/v1/000001bf3d2367c0"],
    #            "justMyCode": true
    #        }
    #    ]
    #}
    slideServiceAndSessIdUrl = sys.argv[1] #for running from MIKAIA

    #alternatively, just init the var here with the URL:
    #slideServiceAndSessIdUrl = 'http://10.54.73.31:9980/MIKAIA/SlideService/v1/000002fadf6ea300'  
    
    #initialize the MIKAIA Slide Service client
    progress_0to1 = 0.01
    print("Connecting to MIKAIA SlideService '{}' ...".format(slideServiceAndSessIdUrl)) 
    ss = mikaia_api.SlideService(slideServiceAndSessIdUrl)
    ss.sendProgress(progress_0to1, 0, 'Running TensorFlow classification sample...') 
    slideInfo = ss.getSlideInfo()

    #load the tensorflow model and define model-specific parameters
    # you can use your own AI model instead.
    progress_0to1 = 0.05
    ss.sendProgress(progress_0to1, 0, 'Loading TensorFlow model...') 
    model = tf.keras.models.load_model("./zoo/colon_classifier_effnet_b0")
    labels = ["Tumor Cells", "Inflammation", "Connective/Fat", "Muscle", "Mucosa", "Mucus", "Necrosis"]
    patchWidth_px = 224
    batchSize = 32

    progress_0to1 = 0.10
    ss.sendProgress(progress_0to1, 0, 'Calculate patch size and number of tiles...') 
    
    #calculate the target input width in um, so that the tiles can be retrieved from MIKAIA in the correct size
    patchWidth_um, patchHeigh_um = px2um(patchWidth_px, slideInfo)

    # get ROIs to analyze from retrieved SlideInfo object
    rois =slideInfo.roi
    
    # Alternatively retrieve the ROIs from the slide (annotations of a certain class e.g. "roi", "Tissue", ...). 
    # rois = ss.getAnnotations("", "roi")

    #go through each roi and calculate the tile coordinates
    tiles = calculateTilesFromRois(rois, patchWidth_um, patchHeigh_um)
    msg = "{} ROI(s) splitted into {} tiles".format(len(rois), len(tiles))
    print(msg)
    ss.sendMessage(msg) 

    if len(tiles) == 0:
        ss.sendMessage("ERROR: ROI absent or too small.") 
        sys.exit("ROI absent or too small.")
        
    #create an annotation class for each label
    progress_0to1 = 0.12
    ss.sendProgress(progress_0to1, 0, 'Create annotation classes for each classification label...') 
    annoClasses = []
    annoClasses.append(ss.createAnnotationClass('Tumor Cells', 'Tumor Cells', 3, '#fff00000', '#ffffcccc', 0.3 ))
    annoClasses.append(ss.createAnnotationClass('Inflammation', 'Inflammation', 3, '#ffffb31a', '#ffffdd99', 0.3 ))
    annoClasses.append(ss.createAnnotationClass('Connective/Fat', 'Connective/Fat', 3, '#ffadad85', '#ffd6d6c2', 0.3 ))
    annoClasses.append(ss.createAnnotationClass('Muscle', 'Muscle', 3, '#ff80bfff', '#ffcce6ff', 0.3 ))
    annoClasses.append(ss.createAnnotationClass('Mucosa', 'Mucosa', 3, '#ffcc66ff', '#ffeeccff', 0.3 ))
    annoClasses.append(ss.createAnnotationClass('Mucus', 'Mucus', 3, '#ffff80ff', '#ffffccff', 0.3 ))
    annoClasses.append(ss.createAnnotationClass('Necrosis', 'Necrosis', 3, '#ff660000' ))
    ss.addAnnotationClasses(annoClasses)

    #set batch-related parameters
    currentBatch = 0 #the batch currently being processed
    numBatches = np.ceil(len(tiles)/batchSize).astype(int) #the number of total batches needed to process all of the tiles

    #iterate through the tiles of each batch, retrieve the tile images, feed them into the model for classification, and send the results back to MIKAIA as annotations
    msg = "Start classification - {} batches a {} tiles".format(numBatches, batchSize)
    print(msg)
    ss.sendMessage(msg)
    
    progressStep = (0.95 - progress_0to1) / (2*numBatches)
    while currentBatch < numBatches:
        # retrieve the tile images for the current batch from MIKAIA and prepare them for classification
        # (for performance reasons, it would be better to retrieve a larger ROI and then split it here into patches)
        progress_0to1 += progressStep
        ss.sendProgress(progress_0to1, 0, 'Batch {} of {}: retrieve tiles...'.format(currentBatch + 1, numBatches)) 

        batch = np.empty(shape=(batchSize, patchWidth_px, patchWidth_px, 3))
        tilesInBatch = batchSize
        for i in range(batchSize):
            tileNumber = currentBatch * batchSize + i
            if tileNumber >= len(tiles):
                #this is the last batch and it is not full
                tilesInBatch = i
                break
            tilecoords = tiles[tileNumber]
            tileImage = ss.getNativeROI(tilecoords[0][0], tilecoords[0][1], patchWidth_px, patchWidth_px)
            batch[i] = np.array(tileImage)[np.newaxis, ...]

        #normalize batch to range used by model: [-1,1]
        batch = (batch/127.5) - 1.0

        #predict 
        progress_0to1 += progressStep
        ss.sendProgress(progress_0to1, 0, 'Batch {} of {}: classify tiles...'.format(currentBatch + 1, numBatches)) 
        results = model.predict(batch)

        # go through the results (softmax), match the result to the label and create the annotation in MIKAIA
        newAnnos = []
        for resultIndex in range(tilesInBatch):
            highestIndex = np.argmax(results[resultIndex])
            label = labels[highestIndex]
            rect_anno = ss.createAnnotation("Rectangle", tiles[currentBatch * batchSize + resultIndex], label)
            newAnnos.append(rect_anno)
        
        ss.addAnnotations(newAnnos)

        currentBatch += 1
        
    progress_0to1 = 1.0
    ss.sendProgress(progress_0to1, 0, 'Classification finished - {} tiles processed'.format(len(tiles))) 

def px2um(patchWidth_px, slideInfo):
    res = slideInfo.nativeResolution #resolution in um/px
    patchWidth_um = patchWidth_px * res.width
    patchHeigh_um = patchWidth_px * res.height
    return patchWidth_um, patchHeigh_um 

def calculateTilesFromRois(rois, patchWidth_um, patchHeigh_um):
    tiles = []
    for roi in rois:

        # TODO: support other types, in particular Polygon and Path
        if roi.shapeType != 'Rectangle':
            print("NOTE: Tiling isn't accurate for ROIs of type '{}': We use the bounding rectangle here!".format(roi.shapeType)) 
        
        br = roi.boundingRect()
        roiX_um = br.x
        roiY_um = br.y
        roiWidth_um = br.width
        roiHeight_um = br.height

        #calculate the number of tiles needed to fill the roi
        numTilesWidth = np.ceil(roiWidth_um/patchWidth_um).astype(int)
        numTilesHeight = np.ceil(roiHeight_um/patchHeigh_um).astype(int)

        #calculate and collect the tile coordinates
        currentCorner = mikaia_api.PointF(roiX_um, roiY_um) #top left corner of current tile
        for y in range(numTilesHeight):
            for x in range(numTilesWidth):
                tile = [[currentCorner.x, currentCorner.y], [currentCorner.x + patchWidth_um, currentCorner.y + patchHeigh_um]]
                tiles.append(tile)
                currentCorner.x +=  patchWidth_um

            currentCorner.x = roiX_um
            currentCorner.y += patchHeigh_um 
    return tiles


if __name__ == "__main__":
    main()