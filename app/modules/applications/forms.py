"""Dover field discovery and exact, verified-answer matching."""
import re

# Verified against the live Dover form: labels are sibling FormLabel divs.
FIELD_INFO = """e => {
  let label = Array.from(e.labels || []).map(x=>x.innerText).join(' ') || e.getAttribute('aria-label') || '';
  for (let p=e.parentElement, depth=0; !label && p && depth<5; p=p.parentElement, depth++) {
    const labels=Array.from(p.children).filter(x => typeof x.className==='string' && x.className.includes('FormLabel'));
    if(labels.length===1) label=labels[0].innerText;
  }
  return {label:label.trim(),name:e.getAttribute('name') || '',
    required:!!e.required || e.getAttribute('aria-required')==='true' || label.includes('*') || !!e.querySelector('input[required]')};
}"""


def normalize(value):
    return re.sub(r'\s+', ' ', str(value).strip().rstrip('*').strip()).casefold()


def answer_for(field, answers):
    """No answer inference from citizenship, total years, or previous defaults."""
    normalized = {normalize(k): str(v).strip() for k, v in answers.items() if str(v).strip()}
    for key in (field['label'], field['name']):
        value = normalized.get(normalize(key))
        if value is not None:
            return value
    return None
