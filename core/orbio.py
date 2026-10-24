"""Server only Orbio advisory client. It has no payment or settlement authority."""
import json
from urllib.error import HTTPError,URLError
from urllib.request import Request,urlopen
from django.conf import settings


class OrbioError(Exception):pass


ACTIONS={
    'scope_summary':'Summarise the agreed scope and identify missing delivery details.',
    'delivery_summary':'Organise the delivery evidence against the acceptance criteria.',
    'dispute_summary':'Prepare a neutral summary of each position and flag missing evidence for a human reviewer.',
}

SYSTEM_PROMPT=(
    'You are the Push Workroom Assistant. Return one JSON object only with these keys: '
    'summary, observations, missing_information, suggested_next_step, escalate_to_human. '
    'observations and missing_information are arrays of short strings. escalate_to_human is a boolean. '
    'You provide an advisory draft. You cannot decide or initiate payments, determine blockchain truth, '
    'select workers, approve profiles, or settle disputes. A human must review your output, and every disputed '
    'settlement requires an authorised human wallet signature. Never invent evidence.'
)


def enabled():
    return bool(settings.PUSH_ORBIO_ASSISTANT_ENABLED and settings.ORBIO_API_KEY and settings.ORBIO_MODEL)


def _context(value):
    allowed=('title','scope','acceptance_criteria','status','messages','deliveries','dispute')
    clean={}
    for key in allowed:
        if key not in value:continue
        item=value[key]
        if isinstance(item,str):clean[key]=item[:4000]
        elif isinstance(item,list):clean[key]=[str(entry)[:1000] for entry in item[:12]]
    return clean


def _validate(value):
    if not isinstance(value,dict):raise OrbioError('Orbio did not return a valid structured response.')
    required={'summary','observations','missing_information','suggested_next_step','escalate_to_human'}
    if not required.issubset(value):raise OrbioError('Orbio did not return a valid structured response.')
    if not isinstance(value['summary'],str) or len(value['summary'])>1200:
        raise OrbioError('Orbio did not return a valid structured response.')
    if not isinstance(value['suggested_next_step'],str) or len(value['suggested_next_step'])>500:
        raise OrbioError('Orbio did not return a valid structured response.')
    for key in ('observations','missing_information'):
        if not isinstance(value[key],list) or len(value[key])>8 or any(not isinstance(v,str) or len(v)>300 for v in value[key]):
            raise OrbioError('Orbio did not return a valid structured response.')
    if not isinstance(value['escalate_to_human'],bool):raise OrbioError('Orbio did not return a valid structured response.')
    return {key:value[key] for key in ('summary','observations','missing_information','suggested_next_step','escalate_to_human')}


def assist(action,context):
    if not enabled():raise OrbioError('The workroom assistant is not enabled.')
    if action not in ACTIONS:raise OrbioError('Choose an available assistant action.')
    body=json.dumps({'model':settings.ORBIO_MODEL,'messages':[
        {'role':'system','content':SYSTEM_PROMPT},
        {'role':'user','content':ACTIONS[action]+'\n\nWorkroom data:\n'+json.dumps(_context(context),separators=(',',':'))},
    ],'max_tokens':700}).encode()
    request=Request(settings.ORBIO_BASE_URL.rstrip('/')+'/chat/completions',data=body,
        headers={'Authorization':'Bearer '+settings.ORBIO_API_KEY,'Content-Type':'application/json'},method='POST')
    try:
        with urlopen(request,timeout=20) as response:payload=json.load(response)
        content=payload['choices'][0]['message']['content']
        return _validate(json.loads(content))
    except OrbioError:raise
    except (HTTPError,URLError,TimeoutError,KeyError,IndexError,TypeError,ValueError,json.JSONDecodeError) as exc:
        raise OrbioError('Orbio did not return a valid structured response.') from exc
