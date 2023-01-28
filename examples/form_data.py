"""
Form Data App
=============

A demo app for submitting form data and files.
"""

from allin import Allin, JSONResponse, status_codes
from allin.errors import HTTPError
from allin.globals import request
from allin.params import UploadFile

app = Allin()

@app.post("/form")
async def form_data():
    if "application/x-www-form-urlencoded" in request.headers.content_type:
        forms = await request.forms()
        return JSONResponse(forms)
    else:
        raise HTTPError(status_codes.BAD_REQUEST, detail="Invalid request. Expected a form-urlencoded request")

@app.post("/file")
async def file_data():
    if "multipart/form-data" in request.headers.content_type:
        forms = await request.forms()
        files = forms.get("files", [])
        # Check if the client, only uploads one file.
        if not isinstance(files, list):
            files = [files]
        
        filenames = []
        for file in files:
            if isinstance(file, UploadFile):
                filenames.append(file.filename)
        detail = "Uploaded" if filenames else "No files uploaded"
        return JSONResponse({"files": filenames, "detail": detail})
    else:
        raise HTTPError(status_codes.BAD_REQUEST, detail="Invalid request. Expected a multipart/form-data request")
