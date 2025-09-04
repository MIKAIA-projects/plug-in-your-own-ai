## MIKAIA Plug-in your-own AI App
MIKAIA comprises off-the-shelf image analysis Apps that are ready to be used, but it also can be extended by users<br>
 - medical users can use the AI Author to interactively train new AI models in MICAIA within minutes. Since the AI Author is based on a Few Shot Learning AI method, it can be trained using only very few annotations<br>
 - technical users can plug in their own AI scripts into MIKAIA and this way make use of the infrastructure provided by MIKAIA. Finanally, they can deploy their AI models and put them into a pathologist's hands, who does not have a linux laptop and cannot run a Python or Matlab script on their own computer. Instead they can use MIKAIA as a UI, which invokes the script and provides APIs to it for reading in pixels or visualizing overlays.  

## plugin scripting language
The user plugin will typically be a Python file, but it could also be an R script, Matlab script or any other executable. <br>
The reason is that MIKAIA does not directly invoke the plugin script. Instead, it turns to a man-in-the-middle, the "script-broker", which discovers local scripts and reports them to MIKAIA, and which invokes the local script as a new process. Afterward, the plugin can communicate directly with the REST server hosted by MIKAIA. 

## where does the plugin run
The the communication protocoll is REST, the plugin can be executed on the same computer as MIKAIA, inside a Docker or on another computer in the network. 

## what is open sourced?
- MIKAIA itself is not open source, but it can be downloaded for free from www.mikaia.ai.
- the MIKAIA Plug-in your own AI App is locked by default in MIKAIA lite. It is unlocked in MIKAIA studio (or get in touch and ask for an eval license).
- the plugin broker is written in Python and made open source. It is found in this repository
- a Python plugin library convenience API is also open source and part of this repository. The library can be imported and contains convenience functionality that simplifies communicaating to the MIKAIA REST server.
- multiple example client plugins are also open sourced and can be found in this repository. As part of one of the examples, a trained AI model (TensorFlow framework) is also open sourced and included in this repository.

## what examples are available?
so far 3 examples are available. 
- one example demonstrates how to use the pixel-access-API and generated-overlay-API. It does not do a meaningful analysis.
- second example segments cells in a selected ROI using pretrained Cellpose model. It demonstrates how to use the pixel-access-API and generated-overlay-API.
- third example analyzes the selected ROI patch by patch with a TensorFlow classification model
- (coming soon) an example of using a foundation model (like UNI or CONCH) to extract image features and cluster them
- (coming soon) an example that carries out segmentation using facebook's segment-anything-model ([SAM](https://github.com/facebookresearch/segment-anything)) 

## Connect your python script to MIKAIA
To run plugin, you have to execute following command in your IDE terminal:
````
python -m mikaia_plugin_api.script_service_server
````

Then start MIKAIA and select Plug-in your own AI App. Select your script in Configuration Tab under "User scripts" dropdown menu.