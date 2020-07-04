import re

from ..app import app
from ..auth import req_admin
from ..tools import OKResponse, ErrorResponse

from ..model.project import Project
from ..model.projectversion import ProjectVersion
from ..model.mirrorkey import MirrorKey


@app.http_post("/api2/mirror")
@req_admin
# FIXME: req_role
async def create_mirror2(request):
    """
    Create a debian mirror.

    ---
    description: Create a debian mirror.
    tags:
        - Mirrors
    consumes:
        - application/x-www-form-urlencoded
    parameters:
        - name: name
          in: query
          required: true
          type: string
          description: name of the mirror
        - name: url
          in: query
          required: true
          type: string
          description: http://host of source
        - name: distribution
          in: query
          required: true
          type: string
          description: trusty, wheezy, jessie, etc.
        - name: components
          in: query
          required: false
          type: array
          description: components to be mirrored
          default: main
        - name: keys
          in: query
          required: false
          type: array
          uniqueItems: true
          collectionFormat: multi
          allowEmptyValue: true
          minItems: 0
          items:
              type: string
          description: repository keys
        - name: keyserver
          in: query
          required: false
          type: string
          description: host name where the keys are
        - name: is_basemirror
          in: query
          required: false
          type: boolean
          description: use this mirror for chroot
        - name: architectures
          in: query
          required: false
          type: array
          description: i386,amd64,arm64,armhf,...
        - name: version
          in: query
          required: false
          type: string
        - name: armored_key_url
          in: query
          required: false
          type: string
        - name: basemirror_id
          in: query
          required: false
          type: string
        - name: download_sources
          in: query
          required: false
          type: boolean
        - name: download_installer
          in: query
          required: false
          type: boolean
    produces:
        - text/json
    responses:
        "200":
            description: successful
        "400":
            description: mirror creation failed.
        "412":
            description: key error.
        "409":
            description: mirror already exists.
        "500":
            description: internal server error.
        "503":
            description: aptly not available.
        "501":
            description: database error occurred.
    """
    params = await request.json()

    mirrorname       = params.get("mirrorname")        # noqa: E221
    mirrorversion    = params.get("mirrorversion")     # noqa: E221
    mirrortype       = params.get("mirrortype")        # noqa: E221
    basemirror       = params.get("basemirror")        # noqa: E221
    mirrorurl        = params.get("mirrorurl")         # noqa: E221
    mirrordist       = params.get("mirrordist")        # noqa: E221
    mirrorcomponents = params.get("mirrorcomponents")  # noqa: E221
    architectures    = params.get("architectures")     # noqa: E221
    mirrorsrc        = params.get("mirrorsrc")         # noqa: E221
    mirrorinst       = params.get("mirrorinst")        # noqa: E221
    mirrorkeyurl     = params.get("mirrorkeyurl")      # noqa: E221
    mirrorkeyids     = params.get("mirrorkeyids")      # noqa: E221
    mirrorkeyserver  = params.get("mirrorkeyserver")   # noqa: E221

    mirrorcomponents = re.split(r"[, ]", mirrorcomponents)

    basemirror_id = None
    if mirrortype == "2":
        base_project, base_version = basemirror.split("/")
        query = request.cirrina.db_session.query(ProjectVersion)
        query = query.join(Project, Project.id == ProjectVersion.project_id)
        query = query.filter(Project.is_mirror.is_(True))
        query = query.filter(Project.name == base_project)
        query = query.filter(ProjectVersion.name == base_version)
        entry = query.first()

        if not entry:
            return ErrorResponse(400, "Invalid basemirror")

        basemirror_id = entry.id

    if not mirrorcomponents:
        mirrorcomponents = ["main"]

    is_basemirror = mirrortype == "1"

    if mirrorkeyurl != "":
        mirrorkeyids = []
        mirrorkeyserver = ""
    elif mirrorkeyids:
        mirrorkeyurl = ""
        mirrorkeyids = re.split(r"[, ]", mirrorkeyids)
    else:
        mirrorkeyurl = ""
        mirrorkeyids = []
        mirrorkeyserver = ""

    args = {
        "create_mirror": [
            mirrorname,
            mirrorurl,
            mirrordist,
            mirrorcomponents,
            mirrorkeyids,
            mirrorkeyserver,
            is_basemirror,
            architectures,
            mirrorversion,
            mirrorkeyurl,
            basemirror_id,
            mirrorsrc,
            mirrorinst,
        ]
    }
    await request.cirrina.aptly_queue.put(args)
    return OKResponse("Mirror creation started")


@app.http_put("/api2/mirror/{name}/{version}")
@req_admin
# FIXME: req_role
async def edit_mirror(request):
    mirror_name = request.match_info["name"]
    mirror_version = request.match_info["version"]
    params = await request.json()

    mirror = request.cirrina.db_session.query(ProjectVersion).join(Project).filter(
                ProjectVersion.project_id == Project.id,
                ProjectVersion.name == mirror_version,
                Project.name == mirror_name).first()
    if not mirror:
        return ErrorResponse(400, "Mirror not found")

    mirrorkey = request.cirrina.db_session.query(MirrorKey).filter(MirrorKey.projectversion_id == mirror.id).first()
    if not mirrorkey:
        return ErrorResponse(400, "Mirror not found")

    if mirror.is_locked:
        return ErrorResponse(400, "Mirror is locked")

    mirrortype       = params.get("mirrortype")        # noqa: E221
    basemirror       = params.get("basemirror")        # noqa: E221
    mirrorurl        = params.get("mirrorurl")         # noqa: E221
    mirrordist       = params.get("mirrordist")        # noqa: E221
    mirrorcomponents = params.get("mirrorcomponents")  # noqa: E221
    architectures    = params.get("architectures")     # noqa: E221
    mirrorsrc        = params.get("mirrorsrc")         # noqa: E221
    mirrorinst       = params.get("mirrorinst")        # noqa: E221
    mirrorkeyurl     = params.get("mirrorkeyurl")      # noqa: E221
    mirrorkeyids     = params.get("mirrorkeyids")      # noqa: E221
    mirrorkeyserver  = params.get("mirrorkeyserver")   # noqa: E221

    basemirror_name, basemirror_version = basemirror.split("/")
    bm = request.cirrina.db_session.query(ProjectVersion).filter(
                ProjectVersion.project.name == basemirror_version,
                ProjectVersion.name == basemirror_name).first()
    if not bm:
        return ErrorResponse(400, "could not find a basemirror with '%s'", basemirror)

    mirror.mirror_url = mirrorurl
    mirror.mirror_distribution = mirrordist
    mirror.mirror_components = mirrorcomponents
    mirror.mirror_architectures = "{" + ", ".join(architectures) + "}"
    mirror.mirror_with_sources = mirrorsrc
    mirror.mirror_with_installer = mirrorinst
    mirror.is_basemirror = mirrortype == "1"
    mirror.basemirror = bm

    mirrorkey.keyurl = mirrorkeyurl
    mirrorkey.keyids = mirrorkeyids
    mirrorkey.keyserver = mirrorkeyserver

    request.cirrina.db_session.commit()

    if mirror.mirror_state == "init_error":
        args = {"init_mirror": [mirror.id]}
    else:
        args = {"update_mirror": [mirror.id]}
    await request.cirrina.aptly_queue.put(args)
    return OKResponse("Mirror update started")
