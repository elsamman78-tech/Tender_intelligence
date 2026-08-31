from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class PortalProfile:
    key: str
    domains: tuple[str,...]
    render_js: bool = False
    source_only_paths: tuple[str,...] = ()
    blocked_path_contains: tuple[str,...] = ()


PROFILES = [
    PortalProfile(
        key='OMAN_ESNAD',
        domains=('etendering.tenderboard.gov.om',),
        render_js=True,
        blocked_path_contains=('mobile','appstore','googleplay'),
    ),
    PortalProfile(
        key='SAUDI_ETIMAD',
        domains=('tenders.etimad.sa',),
        render_js=True,
    ),
    PortalProfile(
        key='QATAR_MONAQASAT',
        domains=('monaqasat.mof.gov.qa',),
        render_js=True,
    ),
    PortalProfile(
        key='IRAQ_ITP',
        domains=('itp.iq',),
        render_js=True,
    ),
    PortalProfile(
        key='KUWAIT_CAPT',
        domains=('capt.gov.kw',),
        blocked_path_contains=('postponement','winning-bids','warranties','closing-tenders'),
    ),
    PortalProfile(
        key='BAHRAIN_TENDER_BOARD',
        domains=('tenderboard.gov.bh','www.tenderboard.gov.bh'),
        blocked_path_contains=(
            'privacy','terms','contact','accessibility','sitemap','faq','annualreports','about/news',
            'standardelectronic','training','eforms','services/process','archivedtenders','procurementplans',
            'prequalifiedvendors','awardedtenders','liveopening','openedbids','tobeopened','legislation',
        ),
    ),
    PortalProfile(
        key='LIBYA_NOC',
        domains=('noc.ly','www.noc.ly'),
    ),
    PortalProfile(
        key='EBRD_PROCUREMENT',
        domains=('ebrd.com','www.ebrd.com'),
        blocked_path_contains=('/what-we-do/','/who-we-are/','board-practice','sectors'),
    ),
    PortalProfile(
        key='UAE_MOF_PROCUREMENT',
        domains=('mof.gov.ae','www.mof.gov.ae'),
        blocked_path_contains=('readspeaker.com','readspeaker'),
    ),
]


def profile_for_host(host: str|None) -> PortalProfile|None:
    h=(host or '').lower()
    for p in PROFILES:
        if any(h==d or h.endswith('.'+d) for d in p.domains):
            return p
    return None
