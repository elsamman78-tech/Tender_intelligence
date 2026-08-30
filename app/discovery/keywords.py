PROCUREMENT_TERMS = [
    'tender','tenders','procurement','request for proposal','request for proposals','rfp','request for expression of interest',
    'expression of interest','eoi','reoi','request for quotation','rfq','invitation to bid','invitation for bids','bid closing',
    'proposal due','submission deadline','terms of reference','tor','consultant selection','prequalification','pre-qualification',
    'general procurement notice','specific procurement notice','tender notice','procurement notice','bidding document','tender document',
    'مناقصة','منافسة','طلب عروض','طلب عرض','إبداء اهتمام','ابداء اهتمام','تأهيل','طرح','كراسة','موعد تقديم العروض',
    'دعوة لتقديم العطاءات','دعوة لتقديم العروض','دعوة الشركات الاستشارية',
    "appel d'offres","manifestation d'intérêt",'demande de propositions','consultation'
]

CONSULTANCY_TERMS = [
    'consultant','consultancy','consulting services','engineering consultancy','engineering consultant','design consultant',
    'design services','construction supervision','supervision consultant','project management consultant','pmc',
    "owner's engineer",'owners engineer',"employer's representative",'lead consultant','cost management','cost consultant',
    'feasibility study','feasibility studies','master planning','master plan consultant','technical assistance','advisory services',
    'project management services','design review','resident engineer','consulting firm','consulting entity','detailed design',
    'concept design','ifc design','engineering design','architectural design','structural design','mep design','infrastructure design',
    'road design','bridge design','water design','wastewater design','desalination design','geotechnical','surveying','bim',
    'environmental and social impact assessment','esia','renewable energy design','transport planning',
    'استشاري','استشارات','خدمات استشارية','مكتب استشاري','تصميم','إشراف','اشراف','إدارة مشاريع','ادارة مشاريع','دراسة جدوى',
    'مخطط عام','مخطط رئيسي','مهندس المالك','مساعدة فنية','تصميم تفصيلي','مكتب هندسي','دراسات هندسية',
    'bureau d’études',"bureau d'etudes",'maîtrise d’oeuvre',"maitrise d'oeuvre",'mission de contrôle',
    'assistance technique','études','supervision'
]

# Strong evidence that the consultancy is inside the engineering / built-environment
# mandate. Generic words such as "consultant", "study" or "design" are intentionally
# excluded because they also occur in training, governance, communications and capacity
# building procurements.
ENGINEERING_DOMAIN_TERMS = [
    'engineering consultancy','engineering consultant','engineering services','engineering design','detailed design',
    'concept design','ifc design','design review','design and supervision','construction supervision','site supervision',
    'supervision consultant','resident engineer','project management consultant','project management consultancy','pmc',
    "owner's engineer",'owners engineer',"employer's representative",'architectural design','architecture consultant',
    'structural design','structural engineering','mep design','mep engineering','electrical engineering','mechanical engineering',
    'civil engineering','infrastructure design','infrastructure consultant','road design','roads and bridges','bridge design',
    'transport planning','rail design','metro design','water design','wastewater design','desalination design','hydraulic design',
    'geotechnical','surveying','topographic survey','bim','master planning','urban planning','urban development',
    'environmental and social impact assessment','environmental impact assessment','esia','renewable energy design',
    'power engineering','energy engineering','oil and gas engineering','pipeline design','feasibility study and design',
    'استشارات هندسية','استشاري هندسي','مكتب هندسي','دراسات هندسية','تصميم هندسي','تصميم تفصيلي','مراجعة التصميم',
    'إشراف على التنفيذ','اشراف على التنفيذ','إشراف هندسي','اشراف هندسي','إدارة مشروعات هندسية','ادارة مشروعات هندسية',
    'طرق وكباري','طرق وجسور','بنية تحتية','مياه وصرف','مياه وصرف صحي','تحلية','ميكانيكا وكهرباء','كهروميكانيك',
    'جيوتقنية','مساحة','تخطيط عمراني','مخطط عام','تقييم الأثر البيئي','مهندس المالك',
    'bureau d’études techniques',"bureau d'etudes techniques",'ingénierie','ingenierie','génie civil','genie civil',
    'maîtrise d’oeuvre',"maitrise d'oeuvre",'mission de contrôle technique','supervision des travaux'
]

SAUDI_DB_TERMS = [
    'design and build','design & build','design-build','epc','epcm','turnkey','engineering procurement construction',
    'contractor shall design','detailed design and construction','design, supply and construction','design construction',
    'تصميم وتنفيذ','تصميم وبناء','الهندسة والتوريد والإنشاء','تسليم مفتاح'
]

PARTNERING_TERMS = [
    'joint venture','jv','consortium','association with','associate with','local partner','local consultant',
    'subconsultant','sub-consultant','lead firm','jointly and severally','national consultant','international consultant',
    'تحالف','ائتلاف','مشروع مشترك','شريك محلي','استشاري محلي','استشاري فرعي'
]

ACTIONABLE_NOTICE_TERMS = [
    'submission deadline','closing date','bid closing','proposal due','deadline','submit proposal','submission of bids',
    'tender reference','reference no','reference number','tender no','rfp no','eoi no','procurement reference',
    'tender documents','bidding documents','request for proposal','expression of interest','invitation to bid',
    'آخر موعد','الموعد النهائي','تقديم العروض','رقم المناقصة','رقم المنافسة','رقم المرجع','كراسة الشروط','شراء الكراسة'
]

NOISE_TERMS = [
    'job vacancy','career','careers','training course','conference','webinar','employment opportunity','وظائف','توظيف','دورة تدريبية',
    'linkedin profile','view profile','people also viewed','followers','connections','personal profile','employee profile',
    'press release','company news','latest news','breaking news','interview with','appointed as','promotion announcement',
    'contract awarded to','wins contract','won the contract','award ceremony','project inaugurated','project launch event'
]

FILE_TERMS = ['rfp','tor','eoi','reoi','tender','addendum','clarification','prequalification','procurement','consultant','consultancy']
DOCUMENT_EXTENSIONS = ('.pdf','.doc','.docx','.xls','.xlsx','.csv','.zip')
PROCUREMENT_PATH_HINTS = ('tender','procurement','business-opportun','rfp','eoi','notice','vendor','consultant','contract','bid')
