# Initial verified public seed library. It is deliberately a seed, not a claim of complete coverage.
# Only sources with a public official procurement/opportunity surface belong here; source discovery expands it continuously.
SEED_SOURCES = [
    {
        'name':'World Bank Procurement Notices','domain':'projects.worldbank.org','base_url':'https://projects.worldbank.org/en/projects-operations/procurement',
        'source_type':'MDB','country':None,'languages':'en,fr,ar','priority':'CRITICAL','trust_score':100,'relevance_score':95,'discovery_value':100,
        'channels':[('TENDERS','https://projects.worldbank.org/en/projects-operations/procurement','HTML'),('EARLY_SIGNALS','https://projects.worldbank.org/en/projects-operations/opportunities','HTML')]
    },
    {
        'name':'UNGM Procurement Opportunities','domain':'ungm.org','base_url':'https://www.ungm.org/Public/Notice',
        'source_type':'UN','country':None,'languages':'en,fr,ar','priority':'CRITICAL','trust_score':100,'relevance_score':90,'discovery_value':95,
        'channels':[('TENDERS','https://www.ungm.org/Public/Notice','HTML'),('AWARDS','https://www.ungm.org/Public/ContractAward/Index/ContractAwards','HTML')]
    },
    {
        'name':'UNDP Procurement Notices','domain':'procurement-notices.undp.org','base_url':'https://procurement-notices.undp.org/',
        'source_type':'UN','country':None,'languages':'en,fr','priority':'CRITICAL','trust_score':100,'relevance_score':92,'discovery_value':96,
        'channels':[('TENDERS','https://procurement-notices.undp.org/','HTML')]
    },
    {
        'name':'African Development Bank Procurement','domain':'afdb.org','base_url':'https://www.afdb.org/en/projects-and-operations/procurement',
        'source_type':'MDB','country':None,'languages':'en,fr','priority':'CRITICAL','trust_score':100,'relevance_score':95,'discovery_value':95,
        'channels':[('EOI','https://www.afdb.org/en/documents/project-related-procurement/procurement-notices/request-for-expression-of-interest','HTML'),('TENDERS','https://www.afdb.org/en/documents/category/specific-procurement-notices','HTML'),('EARLY_SIGNALS','https://www.afdb.org/en/documents/project-related-procurement/procurement-notices/general-procurement-notices','HTML')]
    },
    {
        'name':'Islamic Development Bank Project Procurement','domain':'isdb.org','base_url':'https://www.isdb.org/project-procurement/tenders',
        'source_type':'MDB','country':None,'languages':'en,fr,ar','priority':'CRITICAL','trust_score':100,'relevance_score':98,'discovery_value':98,
        'channels':[('TENDERS','https://www.isdb.org/project-procurement/taxonomy/term/204','HTML'),('EARLY_SIGNALS','https://www.isdb.org/project-procurement/taxonomy/term/207','HTML')]
    },
    {
        'name':'Asian Development Bank Business Opportunities','domain':'adb.org','base_url':'https://www.adb.org/business/project-procurement/business-opportunities',
        'source_type':'MDB','country':None,'languages':'en','priority':'HIGH','trust_score':100,'relevance_score':90,'discovery_value':90,
        'channels':[('TENDERS','https://www.adb.org/business/project-procurement/business-opportunities','HTML')]
    },
    {
        'name':'EBRD Procurement Notices','domain':'ebrd.com','base_url':'https://www.ebrd.com/home/work-with-us/project-procurement/procurement-notices.html',
        'source_type':'MDB','country':None,'languages':'en','priority':'HIGH','trust_score':100,'relevance_score':92,'discovery_value':92,
        'channels':[('TENDERS','https://www.ebrd.com/home/work-with-us/project-procurement/procurement-notices.html','HTML'),('EARLY_SIGNALS','https://www.ebrd.com/home/work-with-us/project-procurement.html','HTML')]
    },
    {
        'name':'TED European Public Procurement','domain':'ted.europa.eu','base_url':'https://ted.europa.eu/en/',
        'source_type':'SUPRANATIONAL_GOVERNMENT','country':None,'languages':'multi','priority':'HIGH','trust_score':100,'relevance_score':88,'discovery_value':95,
        'channels':[('TENDERS','https://ted.europa.eu/en/','HTML')]
    },
    {
        'name':'Egypt Public e-Procurement System','domain':'eps-gags.gov.eg','base_url':'https://www.eps-gags.gov.eg/eb/operation/moveAnoncemtSuplrList.do',
        'source_type':'GOVERNMENT_PORTAL','country':'Egypt','languages':'ar,en','priority':'CRITICAL','trust_score':100,'relevance_score':92,'discovery_value':100,
        'channels':[('TENDERS','https://www.eps-gags.gov.eg/eb/operation/moveAnoncemtSuplrList.do','HTML')]
    },
    {
        'name':'Saudi Etimad Tenders','domain':'tenders.etimad.sa','base_url':'https://tenders.etimad.sa/',
        'source_type':'GOVERNMENT_PORTAL','country':'Saudi Arabia','languages':'ar','priority':'CRITICAL','trust_score':100,'relevance_score':90,'discovery_value':100,
        'channels':[('TENDERS','https://tenders.etimad.sa/Tender','HTML'),('ANNOUNCEMENTS','https://tenders.etimad.sa/Announcement/AllVisitorAnnouncements','HTML')]
    },
    {
        'name':'Bangladesh e-GP','domain':'eprocure.gov.bd','base_url':'https://www.eprocure.gov.bd/',
        'source_type':'GOVERNMENT_PORTAL','country':'Bangladesh','languages':'en,bn','priority':'CRITICAL','trust_score':100,'relevance_score':85,'discovery_value':100,
        'channels':[('TENDERS','https://www.eprocure.gov.bd/resources/common/AllTenders.jsp?h=t','HTML')]
    },
    {
        'name':'UAE Federal Current Business Opportunities','domain':'mof.gov.ae','base_url':'https://mof.gov.ae/en/public-finance/government-procurement/current-business-opportunities/',
        'source_type':'GOVERNMENT_PORTAL','country':'UAE','languages':'ar,en','priority':'CRITICAL','trust_score':100,'relevance_score':92,'discovery_value':100,
        'channels':[('TENDERS','https://mof.gov.ae/en/public-finance/government-procurement/current-business-opportunities/','HTML')]
    },
    {
        'name':'UAE Federal Digital Procurement Platform','domain':'procurement.gov.ae','base_url':'https://procurement.gov.ae/',
        'source_type':'GOVERNMENT_PORTAL','country':'UAE','languages':'ar,en','priority':'CRITICAL','trust_score':100,'relevance_score':85,'discovery_value':95,
        'channels':[('TENDERS','https://procurement.gov.ae/page.aspx/en/buy/homepage','HTML')]
    },
    {
        'name':'Dubai Government eSupply','domain':'esupply.dubai.gov.ae','base_url':'https://esupply.dubai.gov.ae/',
        'source_type':'GOVERNMENT_PORTAL','country':'UAE','languages':'ar,en','priority':'HIGH','trust_score':100,'relevance_score':85,'discovery_value':92,
        'channels':[('TENDERS','https://esupply.dubai.gov.ae/','HTML')]
    },
    {
        'name':'Libya National Oil Corporation Tenders','domain':'noc.ly','base_url':'https://noc.ly/en/tenders/',
        'source_type':'PUBLIC_COMPANY','country':'Libya','languages':'ar,en','priority':'HIGH','trust_score':100,'relevance_score':70,'discovery_value':85,
        'channels':[('TENDERS','https://noc.ly/en/tenders/','HTML')]
    },
    {
        'name':'Oman Tender Board eTendering','domain':'etendering.tenderboard.gov.om','base_url':'https://etendering.tenderboard.gov.om/product/publicDash?CTRL_STRDIRECTION=LTR',
        'source_type':'GOVERNMENT_PORTAL','country':'Oman','languages':'ar,en','priority':'HIGH','trust_score':100,'relevance_score':90,'discovery_value':96,
        'channels':[('TENDERS','https://etendering.tenderboard.gov.om/product/publicDash?CTRL_STRDIRECTION=LTR','HTML')]
    },
    {
        'name':'Qatar Unified State Procurement Monaqasat','domain':'monaqasat.mof.gov.qa','base_url':'https://monaqasat.mof.gov.qa/TendersOnlineServices',
        'source_type':'GOVERNMENT_PORTAL','country':'Qatar','languages':'ar,en','priority':'HIGH','trust_score':100,'relevance_score':92,'discovery_value':96,
        'channels':[('TENDERS','https://monaqasat.mof.gov.qa/TendersOnlineServices/SearchTenders/1','HTML'),('EARLY_SIGNALS','https://monaqasat.mof.gov.qa/TendersOnlineServices','HTML')]
    },
    {
        'name':'Bahrain Tender Board','domain':'tenderboard.gov.bh','base_url':'https://www.tenderboard.gov.bh/tenders/publictenders/',
        'source_type':'GOVERNMENT_PORTAL','country':'Bahrain','languages':'ar,en','priority':'HIGH','trust_score':100,'relevance_score':90,'discovery_value':96,
        'channels':[('TENDERS','https://www.tenderboard.gov.bh/tenders/publictenders/','HTML'),('PREQUALIFICATION','https://etendering.tenderboard.gov.bh/Tenders/publicDash','HTML')]
    },
    {
        'name':'Jordan JONEPS','domain':'joneps.gov.jo','base_url':'https://www.joneps.gov.jo/',
        'source_type':'GOVERNMENT_PORTAL','country':'Jordan','languages':'ar,en','priority':'HIGH','trust_score':100,'relevance_score':90,'discovery_value':96,
        'channels':[('TENDERS','https://joneps.gov.jo/ep/invt/selectListTendInvitAL.do','HTML'),('EARLY_SIGNALS','https://www.joneps.gov.jo/','HTML')]
    },
]
