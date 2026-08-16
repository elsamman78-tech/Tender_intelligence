# Initial verified public seed library. It is deliberately a seed, not a claim of complete coverage.
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
        'name':'Saudi Etimad Tenders','domain':'tenders.etimad.sa','base_url':'https://tenders.etimad.sa/',
        'source_type':'GOVERNMENT_PORTAL','country':'Saudi Arabia','languages':'ar','priority':'CRITICAL','trust_score':100,'relevance_score':90,'discovery_value':100,
        'channels':[('TENDERS','https://tenders.etimad.sa/','HTML'),('ANNOUNCEMENTS','https://tenders.etimad.sa/Announcement/AllVisitorAnnouncements','HTML')]
    },
    {
        'name':'Bangladesh e-GP','domain':'eprocure.gov.bd','base_url':'https://www.eprocure.gov.bd/',
        'source_type':'GOVERNMENT_PORTAL','country':'Bangladesh','languages':'en,bn','priority':'CRITICAL','trust_score':100,'relevance_score':85,'discovery_value':100,
        'channels':[('TENDERS','https://www.eprocure.gov.bd/resources/common/AllTenders.jsp?h=t','HTML')]
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
]
