Hey! Welcome to the PhotoLogger README. It's pretty simple. Scroll to the bottom for directions

Description:
PhotoLogger automatically renames photos from a camera as they’re imported.

Pre-requisites:
- Python 3 installed.
- Google Chrome installed.
- A camera with tethering.
- Windows machine.

==========================NORMAL USE=========================

1. Set up your camera tethering.

2. Double-click "Start_PhotoLogger.bat"

2a. This should launch a CMD prompt and a new chrome tab with an incremental counter.

3. When a customer hands you their receipt, click the plus sign to make the logging number match the receipt ID.

4. Take photos.

5. Repeat adnosium.

6. When done, open powershell and press Ctrl + C to close the python server.

7. Close the Photo Logger HTML page.

Other:

- I recommend creating a shortcut inside of PhotoLogger to the folder where your camera's photos are deposited.
- If you click "+" too many times, there's this amazing "-" button that can make the counter go the OTHER way. Insane stuff. Use that to fix your mistakes.
- Whatever number you're at is saved, so next time you set up the kiosk you won't have to press "+" a hundred times until the IDs match again.

=======================END OF NORMAL USE======================


=======================ON FIRST SETUP====================

1. Open Windows Powershell.

2. Navigate to your PhotoLogger directory through Powershell. If you don't know how to do this, ask an AI or something.

3. Once you're in the directory, type the following command:

python -m pip install -r requirements.txt

3a. You should see a bunch of stuff install. This is good, it means it's working.

4. Plug your camera in, go through any tethering processes it might require (differs depending on which camera you're using).

5. Find the folder your camera stores new photos in. Different cameras have different file storage paths. Locate the folder that new images are stored in. Keep this folder open, you'll need the path in a moment.

6. Now that you know where incoming photos are stored, you lets find the output folder.

6a. You can make this anywhere, but there's already one present in the PhotoLogger folder you installed.

6b. You can name the folder anything, but I recommend keeping it as "Output". Keep that open, you'll need the path in a moment.

7. Back in the PhotoLogger folder (not through Powershell), right click "photologger_server.py" and select Edit. If you have 
   a programming editor you'd prefer to use, go ahead, but Notepad will work just fine.

8. Look for the Config. It's at the top of the file and labelled like so:

# ---------------------- CONFIG ----------------------

9. For the INCOMING_DIR, change the path in the quotations to match the folder from your camera that new files are stored.

10. For the OUTPUT_DIR, change the path in the quotations to match the folder in the PhotoLogger folder.

11. Save and close the file, and now you're ready to go. Double click "Start_PhotoLogger.bat" to begin the process.

=======================END OF FIRST SETUP====================


