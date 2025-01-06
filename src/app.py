# |-----------------------------------------------------------------------------
# |            This source code is provided under the Apache 2.0 license      --
# |  and is provided AS IS with no warranty or guarantee of fit for purpose.  --
# |                See the project's LICENSE.md for details.                  --
# |           Copyright LSEG 2025. All rights reserved.                       --
# |-----------------------------------------------------------------------------


#!/usr/bin/env python
import os
import lseg.data as ld
from lseg.data import session
import datetime
import json
import base64
import zlib


ld.open_session(config_name='./lseg-data.devrel.config.json')

ld.close_session()