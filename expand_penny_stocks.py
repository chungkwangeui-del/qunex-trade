"""
페니스톡 종목 확장 전략 및 추가 종목 리스트
"""

print("=" * 100)
print("페니스톡 종목 확장 전략")
print("=" * 100)

print("""
[현재 상태]
- 현재 종목 수: 약 210개
- 데이터 기간: 2022-01 ~ 2025-10 (약 3.8년)
- 현재 데이터: 232개 종목 (일부 필터링됨)

[확장 전략]

1. 추가할 종목 카테고리:
   - OTC Markets (OTCQB, Pink Sheets) 고변동성 종목
   - Recent IPO 페니스톡 (2023-2025)
   - 섹터 특화 추가 (AI, 양자컴퓨팅, 바이오테크, EV)
   - 해외 페니스톡 (캐나다, 호주 등)
   - SPAC 합병 종목

2. 목표:
   - 종목 수: 210개 → 400-500개
   - 예상 데이터 증가: 215K rows → 500K+ rows
   - 급등 케이스 증가: 더 많은 학습 데이터

3. 장점:
   [+] 더 다양한 패턴 학습
   [+] 모델 일반화 능력 향상
   [+] 특정 종목 편향 감소
   [+] 급등 케이스 증가로 정확도 향상

4. 주의사항:
   [!] 학습 시간 증가 (1-2시간 → 3-4시간)
   [!] 메모리 사용량 증가
   [!] 일부 종목은 데이터 부족 가능
   [!] OTC 종목은 유동성 낮을 수 있음
""")

print("\n" + "=" * 100)
print("추가 추천 종목 리스트 (200+ 종목)")
print("=" * 100)

additional_tickers = {
    'OTC_HIGH_VOLUME': [
        # OTC Markets - 고거래량 페니스톡
        'HQGE', 'GVSI', 'LTUM', 'WNFT', 'IFXY', 'GDET',
        'DUTV', 'MINE', 'TSNP', 'TLSS', 'ALPP', 'ABML',
        'MNGG', 'MYDX', 'BRLL', 'CELZ', 'AITX', 'GTEH',
        'PJET', 'RTON', 'USMJ', 'HEMP', 'MCOA', 'GRCU',
        'TRTC', 'VATE', 'INND', 'VDRM', 'ECEZ', 'TAUG',
        'PVDG', 'CLSH', 'VPER', 'FDBL', 'FDCT', 'BTCS',
        'AVVH', 'AZFL', 'BVTK', 'CELZ', 'CGRA', 'CHUC',
        'CRWG', 'DSCR', 'EEENF', 'ENKN', 'EPAZ', 'EVSV',
    ],

    'AI_QUANTUM_2024_2025': [
        # AI & 양자컴퓨팅 신규 급등주
        'QBTS',   # D-Wave Quantum
        'LUNR',   # Intuitive Machines
        'DTST',   # Data Storage Corp
        'CXAI',   # CXApp Inc
        'VTEX',   # VTEX (e-commerce AI)
        'BBAI',   # BigBear.ai
        'BKSY',   # BlackSky Technology
        'SPIR',   # Spire Global
        'PATH',   # UiPath (RPA)
        'NCNO',   # nCino (banking AI)
        'DOCN',   # DigitalOcean
        'RSKD',   # Riskified
        'BRZE',   # Braze Inc
        'AMBA',   # Ambarella (AI vision)
        'SMTC',   # Semtech Corp
        'FORM',   # FormFactor
        'LITE',   # Lumentum Holdings
        'HIMX',   # Himax Technologies
        'UCTT',   # Ultra Clean Holdings
        'MKSI',   # MKS Instruments
    ],

    'BIOTECH_CLINICAL_TRIALS': [
        # 바이오테크 임상시험 단계 (고변동성)
        'ABEO',   # Abeona Therapeutics
        'ACRS',   # Aclaris Therapeutics
        'ADVM',   # Adverum Biotechnologies
        'AGIO',   # Agios Pharmaceuticals
        'ALNA',   # Allena Pharmaceuticals
        'ALNY',   # Alnylam Pharmaceuticals
        'ALPN',   # Alpine Immune Sciences
        'ANIK',   # Anika Therapeutics
        'APLS',   # Apellis Pharmaceuticals
        'APLT',   # Applied Therapeutics
        'APRE',   # Aprea Therapeutics
        'ARAV',   # Aravive Inc
        'ARCT',   # Arcturus Therapeutics
        'ARGX',   # argenx SE
        'ASMB',   # Assembly Biosciences
        'AUPH',   # Aurinia Pharmaceuticals
        'AVEO',   # AVEO Pharmaceuticals
        'AVIR',   # Atea Pharmaceuticals
        'AVXL',   # Anavex Life Sciences
        'AXSM',   # Axsome Therapeutics
        'BDTX',   # Black Diamond Therapeutics
        'BHVN',   # Biohaven Pharmaceutical
        'BIIB',   # Biogen Inc
        'BPMC',   # Blueprint Medicines
        'BTAI',   # BioXcel Therapeutics
        'BYSI',   # BeyondSpring Inc
        'CARA',   # Cara Therapeutics
        'CLDX',   # Celldex Therapeutics
        'CMMB',   # Chemomab Therapeutics
        'CNTA',   # Centessa Pharmaceuticals
        'CORT',   # Corcept Therapeutics
        'CRNX',   # Crinetics Pharmaceuticals
        'CRSP',   # CRISPR Therapeutics
        'CRVS',   # Corvus Pharmaceuticals
        'CTMX',   # CytomX Therapeutics
        'CVAC',   # CureVac NV
        'CYCN',   # Cyclerion Therapeutics
        'CYTK',   # Cytokinetics Inc
        'DAWN',   # Day One Biopharmaceuticals
        'DNLI',   # Denali Therapeutics
        'DSGN',   # Design Therapeutics
        'DVAX',   # Dynavax Technologies
        'EIGR',   # Eiger BioPharmaceuticals
        'ELVN',   # Enliven Therapeutics
        'EPIX',   # ESSA Pharma
        'ERAS',   # Erasca Inc
        'ESPR',   # Esperion Therapeutics
        'ETNB',   # 89bio Inc
        'EVLO',   # Evelo Biosciences
        'FATE',   # Fate Therapeutics
        'FDMT',   # 4D Molecular Therapeutics
        'FOLD',   # Amicus Therapeutics
        'FGEN',   # FibroGen Inc
        'FMTX',   # Forma Therapeutics
        'GERN',   # Geron Corporation
        'GILD',   # Gilead Sciences
        'GLPG',   # Galapagos NV
        'GLUE',   # Monte Rosa Therapeutics
        'GOSS',   # Gossamer Bio
        'HALO',   # Halozyme Therapeutics
        'HGEN',   # Humanigen Inc
        'HOFV',   # Hall of Fame Resort
        'HRTX',   # Heron Therapeutics
        'IGMS',   # IGM Biosciences
        'IMAB',   # I-Mab
        'IMCR',   # Immunocore Holdings
        'IMGN',   # ImmunoGen Inc
        'IMMP',   # Immutep Limited
        'INCY',   # Incyte Corporation
        'IONS',   # Ionis Pharmaceuticals
        'IOVA',   # Iovance Biotherapeutics
        'IRWD',   # Ironwood Pharmaceuticals
        'ITCI',   # Intra-Cellular Therapies
        'JANX',   # Janux Therapeutics
        'KALA',   # Kala Pharmaceuticals
        'KALV',   # KalVista Pharmaceuticals
        'KPTI',   # Karyopharm Therapeutics (이미 있음)
        'KRYS',   # Krystal Biotech
        'KYMR',   # Kymera Therapeutics
        'KZIA',   # Kazia Therapeutics
        'LEGN',   # Legend Biotech
        'LIFE',   # aTyr Pharma
        'LIPO',   # Lipocine Inc
        'LTRN',   # Lantern Pharma
        'LUNA',   # Luna Innovations
        'LYEL',   # Lyell Immunopharma
        'MCRB',   # Seres Therapeutics
        'MDGL',   # Madrigal Pharmaceuticals
        'MGNX',   # MacroGenics Inc
        'MNKD',   # MannKind Corporation
        'MOLN',   # Molecular Partners
        'MRUS',   # Merus NV
        'MTEM',   # Molecular Templates
        'MYGN',   # Myriad Genetics
        'NARI',   # Inari Medical
        'NBIX',   # Neurocrine Biosciences
        'NCNA',   # NuCana plc
        'NKTX',   # Nkarta Inc
        'NMTC',   # NeuroOne Medical
        'NTLA',   # Intellia Therapeutics (이미 있음)
        'NTRA',   # Natera Inc
        'NUVB',   # Nuvation Bio
        'NVTA',   # Invitae Corporation
        'NWBO',   # Northwest Biotherapeutics
        'OCGN',   # Ocugen Inc (이미 있음)
        'OMER',   # Omeros Corporation
        'ONCT',   # Oncternal Therapeutics
        'ONEM',   # 1Life Healthcare
        'ORTX',   # Orchard Therapeutics
        'OSPN',   # OneSpan Inc
        'PCVX',   # Vaxcyte Inc
        'PDFS',   # PDF Solutions
        'PGEN',   # Precigen Inc
        'PHAT',   # Phathom Pharmaceuticals
        'PIRS',   # Pieris Pharmaceuticals
        'PRTK',   # Paratek Pharmaceuticals
        'PRVB',   # Provention Bio
        'PTCT',   # PTC Therapeutics
        'PTGX',   # Protagonist Therapeutics
        'PTRA',   # Proterra Inc (이미 있음)
        'RLAY',   # Relay Therapeutics
        'RPTX',   # Repare Therapeutics
        'RPRX',   # Royalty Pharma
        'RUBY',   # Rubius Therapeutics
        'SAGE',   # Sage Therapeutics
        'SANA',   # Sana Biotechnology
        'SEEL',   # Seelos Therapeutics (이미 있음)
        'SGMO',   # Sangamo Therapeutics (이미 있음)
        'SHLS',   # Shoals Technologies
        'SIGA',   # SIGA Technologies
        'SITM',   # SiTime Corporation
        'SLDB',   # Solid Biosciences
        'SNDX',   # Syndax Pharmaceuticals
        'SRRK',   # Scholar Rock Holding
        'STOK',   # Stoke Therapeutics
        'SYRS',   # Syros Pharmaceuticals (이미 있음)
        'TARS',   # Tarsus Pharmaceuticals
        'TBPH',   # Theravance Biopharma
        'TCDA',   # Tricida Inc
        'TERN',   # Terns Pharmaceuticals
        'TGTX',   # TG Therapeutics (이미 있음)
        'TYME',   # Tyme Technologies
        'TYRA',   # Tyra Biosciences
        'VERA',   # Vera Therapeutics
        'VCEL',   # Vericel Corporation
        'VCYT',   # Veracyte Inc
        'VKTX',   # Viking Therapeutics (이미 있음)
        'VKTX',   # Viking Therapeutics
        'VRCA',   # Verrica Pharmaceuticals
        'VRDN',   # Viridian Therapeutics
        'VRNA',   # Verona Pharma
        'VRTX',   # Vertex Pharmaceuticals (이미 있음)
        'VYGR',   # Voyager Therapeutics
        'WINT',   # Windtree Therapeutics
        'XNCR',   # Xencor Inc
        'XTNT',   # Xtant Medical
        'YMAB',   # Y-mAbs Therapeutics
        'YMTX',   # Yumanity Therapeutics
        'ZIXI',   # Zix Corporation
        'ZNTL',   # Zentalis Pharmaceuticals
        'ZYME',   # Zymeworks Inc
    ],

    'RECENT_IPO_2023_2025': [
        # 2023-2025 신규 상장 페니스톡
        'RDDT',   # Reddit (2024 IPO)
        'ARM',    # ARM Holdings (2023 IPO) - 이미 있음
        'DASH',   # DoorDash
        'COIN',   # Coinbase (이미 있음)
        'HOOD',   # Robinhood (이미 있음)
        'RBLX',   # Roblox
        'DIDI',   # DiDi Global
        'GRAB',   # Grab Holdings
        'ASTS',   # AST SpaceMobile
        'BROS',   # Dutch Bros
        'FROG',   # JFrog Ltd
        'GLBE',   # Global-E Online
        'WYNN',   # Wynn Resorts
        'ZS',     # Zscaler
        'CRWD',   # CrowdStrike
        'DDOG',   # Datadog
        'NET',    # Cloudflare
        'SNOW',   # Snowflake
        'U',      # Unity Software
    ],

    'EV_GREEN_ENERGY': [
        # EV & 그린에너지 추가
        'PLUG',   # Plug Power
        'FCEL',   # FuelCell Energy
        'BE',     # Bloom Energy
        'BLDP',   # Ballard Power Systems
        'CLNE',   # Clean Energy Fuels
        'ENPH',   # Enphase Energy
        'SEDG',   # SolarEdge Technologies
        'RUN',    # Sunrun Inc
        'NOVA',   # Sunnova Energy (이미 있음)
        'CSIQ',   # Canadian Solar
        'JKS',    # JinkoSolar
        'SPWR',   # SunPower Corporation
        'MAXN',   # Maxeon Solar Technologies
        'ARRY',   # Array Technologies
        'SHLS',   # Shoals Technologies (이미 있음)
        'NEP',    # NextEra Energy Partners
        'AY',     # Atlantica Sustainable
        'CWEN',   # Clearway Energy
        'BEPC',   # Brookfield Renewable
        'ORA',    # Ormat Technologies
    ],

    'CRYPTO_BLOCKCHAIN': [
        # 크립토/블록체인 추가
        'MARA',   # Marathon Digital (이미 있음)
        'RIOT',   # Riot Platforms (이미 있음)
        'CLSK',   # CleanSpark (이미 있음)
        'CIFR',   # Cipher Mining (이미 있음)
        'WULF',   # TeraWulf Inc
        'IREN',   # Iris Energy (이미 있음)
        'CORZ',   # Core Scientific
        'BTDR',   # Bitdeer Technologies
        'BTBT',   # Bit Digital (이미 있음)
        'APLD',   # Applied Digital (이미 있음)
        'GREE',   # Greenidge Generation (이미 있음)
        'ARBK',   # Argo Blockchain (이미 있음)
        'DGHI',   # Digihost Technology
        'SDIG',   # Stronghold Digital (이미 있음)
    ],

    'SPAC_DSPAC': [
        # SPAC & De-SPAC 종목
        'PSFE',   # Paysafe Limited
        'OPEN',   # Opendoor Technologies
        'SKLZ',   # Skillz Inc (이미 있음)
        'GENI',   # Genius Sports
        'DKNG',   # DraftKings
        'BODY',   # The Beachbody Company
        'BARK',   # BARK Inc
        'TALK',   # Talkspace Inc
        'ME',     # 23andMe
        'IRNT',   # IronNet Inc (이미 있음)
        'OUST',   # Ouster Inc
        'LAZR',   # Luminar Technologies
        'VLDR',   # Velodyne Lidar
        'MKFG',   # Markforged Holding
        'DM',     # Desktop Metal
        'NNDM',   # Nano Dimension
        'MTTR',   # Matterport (이미 있음)
        'SLDP',   # Solid Power
        'QS',     # QuantumScape (이미 있음)
    ],

    'CANNABIS_PSYCHEDELICS': [
        # 대마초 & 환각제 치료
        'TLRY',   # Tilray (이미 있음)
        'CGC',    # Canopy Growth (이미 있음)
        'SNDL',   # Sundial Growers (이미 있음)
        'ACB',    # Aurora Cannabis (이미 있음)
        'CRON',   # Cronos Group (이미 있음)
        'HEXO',   # HEXO Corp
        'OGI',    # OrganiGram Holdings
        'CURLF',  # Curaleaf Holdings (이미 있음)
        'GTBIF',  # Green Thumb Industries (이미 있음)
        'TCNNF',  # Trulieve Cannabis (이미 있음)
        'CRLBF',  # Cresco Labs (이미 있음)
        'MSOS',   # AdvisorShares Pure US Cannabis ETF
        'YOLO',   # AdvisorShares Pure Cannabis ETF
        'CMPS',   # Compass Pathways (환각제 치료)
        'ATAI',   # ATAI Life Sciences
        'MNMD',   # Mind Medicine
        'FTRP',   # Field Trip Health
        'NUMI',   # Numinus Wellness
    ],
}

# 통계 출력
print("\n[추가 종목 카테고리별 통계]")
total_new = 0
for category, tickers in additional_tickers.items():
    print(f"\n{category}:")
    print(f"  - 종목 수: {len(tickers)}개")
    print(f"  - 샘플: {', '.join(tickers[:5])}")
    total_new += len(tickers)

print(f"\n" + "=" * 100)
print(f"총 추가 종목: {total_new}개")
print(f"기존 종목: ~210개")
print(f"예상 총 종목: ~{210 + total_new}개")
print("=" * 100)

print("""
\n[다음 단계]
1. data_collector.py에 추가 종목 병합
2. download_3year_data.py 실행 (새로운 종목 다운로드)
3. train_god_model.py 재실행 (확장된 데이터로 재학습)
4. 백테스트 비교 (성능 향상 확인)

[예상 소요 시간]
- 데이터 다운로드: 1-2시간 (400+ 종목)
- 모델 학습: 3-4시간 (500K+ rows)
- 총 소요 시간: 4-6시간

진행하시겠습니까?
""")
