const sources = {
  ucl: {path:'soccer/uefa.champions', label:['Champions League','챔피언스리그'], official:'https://www.uefa.com/uefachampionsleague/fixtures-results/'},
  uel: {path:'soccer/uefa.europa', label:['Europa League','유로파리그'], official:'https://www.uefa.com/uefaeuropaleague/fixtures-results/'},
  epl: {path:'soccer/eng.1', label:['Premier League','프리미어리그'], official:'https://www.premierleague.com/en/matches/premier-league/2026-27'},
  championship: {path:'soccer/eng.2', label:['Championship','잉글랜드 챔피언십']},
  laliga: {path:'soccer/esp.1', label:['La Liga','프리메라리가'], official:'https://www.laliga.com/en-GB/laliga-easports'},
  eredivisie: {path:'soccer/ned.1', label:['Eredivisie','네덜란드 에레디비시']},
  jupiler: {path:'soccer/bel.1', label:['Jupiler Pro League','벨기에 주필러 프로리그']},
  primeira: {path:'soccer/por.1', label:['Primeira Liga','포르투갈 프리메이라리가']},
  scottish: {path:'soccer/sco.1', label:['Scottish Premiership','스코틀랜드 프리미어십']},
  bundesliga: {path:'soccer/ger.1', label:['Bundesliga','분데스리가'], official:'https://www.bundesliga.com/en/bundesliga/matchday'},
  seriea: {path:'soccer/ita.1', label:['Serie A','세리에 A'], official:'https://en.legaseriea.it/serie-a/fixtures-results'},
  ligue1: {path:'soccer/fra.1', label:['Ligue 1','리그앙'], official:'https://ligue1.com/en/calendar/ligue1'},
  j1: {path:'soccer/jpn.1', label:['J1 League','J1리그'], official:'https://www.jleague.jp/en/j1/match/'},
  mls: {path:'soccer/usa.1', label:['MLS','미국 MLS'], official:'https://www.mlssoccer.com/schedule/2026/'},
  mlb: {path:'baseball/mlb', label:['MLB','MLB'], official:'https://www.mlb.com/schedule'},
  nba: {path:'basketball/nba', label:['NBA','NBA'], official:'https://www.nba.com/games'},
  wnba: {path:'basketball/wnba', label:['WNBA','WNBA']},
  nhl: {path:'hockey/nhl', label:['NHL','미국 NHL']},
  khl: {label:['KHL','러시아 KHL']},
  npb: {label:['NPB','NPB 라인업']},
  cpbl: {label:['CPBL','CPBL 라인업']},
  kleague1: {label:['K League 1','K리그1']},
  kleague2: {label:['K League 2','K리그2']},
  ncaam: {path:'basketball/mens-college-basketball', label:["NCAA Men's Basketball",'NCAA 남자농구']},
  kbo: {label:['KBO lineups','KBO 라인업']},
  kbl: {label:['KBL lineups','KBL 라인업']},
  wkbl: {label:['WKBL lineups','WKBL 라인업']},
  kovo: {label:['KOVO lineups','KOVO 라인업']}
};
const sports = [{id:'football',label:['⚽ Football lineups','⚽ 축구 라인업']},{id:'mlb',label:['MLB lineups','MLB 라인업']},{id:'npb',label:['NPB lineups','NPB 라인업']},{id:'cpbl',label:['CPBL lineups','CPBL 라인업']},{id:'nba',label:['NBA lineups','NBA 라인업']},{id:'wnba',label:['WNBA lineups','WNBA 라인업']},{id:'nhl',label:['NHL lineups','NHL 라인업']},{id:'khl',label:['KHL lineups','KHL 라인업']},{id:'kbo',label:['KBO lineups','KBO 라인업']},{id:'kbl',label:['KBL lineups','KBL 라인업']},{id:'wkbl',label:['WKBL lineups','WKBL 라인업']},{id:'kovo',label:['KOVO lineups','KOVO 라인업']}];
const categories = [{id:'football',label:['⚽ Football lineups','⚽ 축구 라인업'],sports:['football']},{id:'baseball',label:['⚾ Baseball lineups','⚾ 야구 라인업'],sports:['mlb','kbo','npb','cpbl']},{id:'basketball',label:['🏀 Basketball lineups','🏀 농구 라인업'],sports:['nba','kbl','wkbl','wnba']},{id:'volleyball',label:['🏐 Volleyball lineups','🏐 배구 라인업'],sports:['kovo']},{id:'hockey',label:['🏒 Hockey lineups','🏒 하키 라인업'],sports:['nhl','khl']}];
const leagueIds = ['ucl','uel','epl','championship','laliga','bundesliga','seriea','ligue1','kleague1','kleague2','eredivisie','jupiler','primeira','scottish','j1','mls'];
const dropdownLeagueNames = {
  "ucl": "UEFA 챔피언스리그",
  "uel": "UEFA 유로파리그",
  "epl": "잉글랜드 프리미어리그",
  "championship": "잉글랜드 EFL 챔피언십",
  "laliga": "스페인 라리가",
  "bundesliga": "독일 분데스리가",
  "seriea": "이탈리아 세리에 A",
  "ligue1": "프랑스 리그 1",
  "kleague1": "대한민국 K리그1",
  "kleague2": "대한민국 K리그2",
  "eredivisie": "네덜란드 에레디비시",
  "jupiler": "벨기에 주필러 프로리그",
  "primeira": "포르투갈 프리메이라리가",
  "scottish": "스코틀랜드 프리미어십",
  "j1": "일본 J1리그",
  "mls": "미국 메이저리그 사커 (MLS)",
  "mlb": "미국 메이저리그 베이스볼 (MLB)",
  "kbo": "대한민국 프로야구 (KBO 리그)",
  "npb": "일본 프로야구 (NPB)",
  "cpbl": "대만 중화직업봉구대연맹 (CPBL)",
  "nba": "미국 프로농구 (NBA)",
  "kbl": "대한민국 남자 프로농구 (KBL)",
  "wkbl": "대한민국 여자 프로농구 (WKBL)",
  "wnba": "미국 여자 프로농구 (WNBA)",
  "kovo": "대한민국 프로배구 V-리그 (KOVO)",
  "nhl": "북미 내셔널 하키 리그 (NHL)",
  "khl": "러시아 콘티넨탈 하키 리그 (KHL)"
};
const dropdownLeagueFlags = {
  "ucl": "🇪🇺",
  "uel": "🇪🇺",
  "epl": "🏴󠁧󠁢󠁥󠁮󠁧󠁿",
  "championship": "🏴󠁧󠁢󠁥󠁮󠁧󠁿",
  "laliga": "🇪🇸",
  "bundesliga": "🇩🇪",
  "seriea": "🇮🇹",
  "ligue1": "🇫🇷",
  "kleague1": "🇰🇷",
  "kleague2": "🇰🇷",
  "eredivisie": "🇳🇱",
  "jupiler": "🇧🇪",
  "primeira": "🇵🇹",
  "scottish": "🏴󠁧󠁢󠁳󠁣󠁴󠁿",
  "j1": "🇯🇵",
  "mls": "🇺🇸",
  "mlb": "🇺🇸",
  "kbo": "🇰🇷",
  "npb": "🇯🇵",
  "cpbl": "🇹🇼",
  "nba": "🇺🇸",
  "kbl": "🇰🇷",
  "wkbl": "🇰🇷",
  "wnba": "🇺🇸",
  "kovo": "🇰🇷",
  "nhl": "🇺🇸🇨🇦",
  "khl": "🇷🇺"
};
const dropdownLeagueLabel = id => id === 'kbo' ? '대한민국 프로야구 (KBO)' : dropdownLeagueNames[id];
const dropdownLeagueOrder = {
  football:['kleague1','kleague2','ucl','uel','epl','championship','laliga','bundesliga','seriea','ligue1','eredivisie','jupiler','primeira','scottish','j1','mls'],
  baseball:['kbo','mlb','npb','cpbl'],
  basketball:['kbl','wkbl','nba','wnba']
};
const leagueLogos = {
  ucl:'https://a.espncdn.com/i/leaguelogos/soccer/500/2.png',uel:'https://a.espncdn.com/i/leaguelogos/soccer/500/2310.png',epl:'https://a.espncdn.com/i/leaguelogos/soccer/500/23.png',championship:'https://a.espncdn.com/i/leaguelogos/soccer/500/24.png',laliga:'https://a.espncdn.com/i/leaguelogos/soccer/500/15.png',bundesliga:'https://a.espncdn.com/i/leaguelogos/soccer/500/10.png',seriea:'https://a.espncdn.com/i/leaguelogos/soccer/500/12.png',ligue1:'https://a.espncdn.com/i/leaguelogos/soccer/500/9.png',eredivisie:'https://a.espncdn.com/i/leaguelogos/soccer/500/11.png',jupiler:'https://a.espncdn.com/i/leaguelogos/soccer/500/6.png',primeira:'https://a.espncdn.com/i/leaguelogos/soccer/500/14.png',scottish:'https://a.espncdn.com/i/leaguelogos/soccer/500/45.png',j1:'https://a.espncdn.com/i/leaguelogos/soccer/500/2199.png',mls:'https://a.espncdn.com/i/leaguelogos/soccer/500/19.png',mlb:'https://a.espncdn.com/i/teamlogos/leagues/500/mlb.png',nba:'https://a.espncdn.com/i/teamlogos/leagues/500/nba.png',wnba:'https://a.espncdn.com/i/teamlogos/leagues/500/wnba.png',nhl:'https://a.espncdn.com/i/teamlogos/leagues/500/nhl.png',khl:'https://www.khl.ru/local/templates/2025/images/logos/2026_27/khl_ru.svg',kleague1:'https://app.holoduke.nl/footapi/images/leagueimages/SouthKoreaKLeagueClassic.png',kleague2:'https://assets.fclogo.top/png/k-league-2-v2021.png',kbo:'https://upload.wikimedia.org/wikipedia/commons/6/6a/Korea_Baseball_Organization_-_2022_wordmark.svg',npb:'https://upload.wikimedia.org/wikipedia/commons/7/7f/NPB_logo.svg',cpbl:'https://www.cpbl.com.tw/theme/common/images/project/logo_new.png',kbl:'https://www.kbl.or.kr/assets/img/logo/logo-header.svg',wkbl:'https://www.wkbl.or.kr/static/images/about/ci_2023.png',kovo:'https://phinf.pstatic.net/tvcast/20241024_232/6A6Ja_1729757946529X0C9l_JPEG/1729757946519.jpg'
};
function leagueButton(id,item,attribute,selected) {
  const initials=id.toUpperCase().replace('KLEAGUE','K');
  const logo=leagueLogos[id] ? `<img class="league-logo" src="${leagueLogos[id]}" alt="" aria-hidden="true" loading="lazy">` : '';
  return `<button type="button" ${attribute}="${id}" aria-current="${selected}"><span class="league-logo-wrap">${logo}<span class="league-logo-fallback" ${logo?'hidden':''}>${initials}</span></span><span>${label(...item.label)}</span></button>`;
}

const extraKo = {'FC Seoul':'FC 서울','Ulsan HD FC':'울산 HD FC','Jeonbuk Hyundai Motors FC':'전북 현대 모터스','Gangwon FC':'강원 FC','Daejeon Hana Citizen':'대전 하나 시티즌','Jeju SK':'제주 SK','Incheon United':'인천 유나이티드','FC Anyang':'FC 안양','Pohang Steelers':'포항 스틸러스','Gimcheon Sangmu':'김천 상무','Bucheon FC 1995':'부천 FC 1995','Gwangju FC':'광주 FC','Dinamo Minsk':'디나모 민스크','Dynamo Msk':'디나모 모스크바','Dinamo Mn':'디나모 민스크','SKA':'SKA 상트페테르부르크','Ak Bars':'아크 바르스','Spartak':'스파르타크 모스크바','Sibir':'시비르 노보시비르스크','Avtomobilist':'아브토모빌리스트','Metallurg Mg':'메탈루르그 마그니토고르스크','Salavat Yulaev':'살라바트 율라예프','Traktor':'트락토르 첼랴빈스크','Avangard':'아방가르드 옴스크','Shanghai Dragons':'상하이 드래곤즈','Admiral':'아드미랄 블라디보스토크','Amur':'아무르 하바롭스크','HC Sochi':'HC 소치','Barys':'바리스 아스타나','Lokomotiv':'로코모티프 야로슬라블','CSKA':'CSKA 모스크바','Neftekhimik':'네프테히미크','Torpedo':'토르페도 니즈니노브고로드','Lada':'라다 톨리야티','Manchester City':'맨체스터 시티','Manchester United':'맨체스터 유나이티드','Bayern Munich':'바이에른 뮌헨','Borussia Dortmund':'보루시아 도르트문트','Paris Saint-Germain':'파리 생제르맹','Real Madrid':'레알 마드리드','Inter Milan':'인터 밀란','Internazionale':'인터 밀란','AC Milan':'AC 밀란','RB Leipzig':'RB 라이프치히','Atlético Madrid':'아틀레티코 마드리드','Newcastle United':'뉴캐슬 유나이티드','Tottenham Hotspur':'토트넘 홋스퍼','Nottingham Forest':'노팅엄 포리스트','Slavia Prague':'슬라비아 프라하','Fenerbahce':'페네르바흐체','Slovan Bratislava':'슬로반 브라티슬라바','AS Roma':'AS 로마','FC Porto':'FC 포르투','AEK Athens':'AEK 아테네','Bodo/Glimt':'보되/글림트','VIKING FK':'비킹 FK','LASK Linz':'LASK 린츠','Los Angeles Dodgers':'LA 다저스','Milwaukee Brewers':'밀워키 브루어스','Tampa Bay Rays':'템파베이 레이스','Cleveland Guardians':'클리블랜드 가디언스','Atlanta Hawks':'애틀랜타 호크스','Boston Celtics':'보스턴 셀틱스','Brooklyn Nets':'브루클린 네츠','Charlotte Hornets':'샬럿 호네츠','Chicago Bulls':'시카고 불스','Cleveland Cavaliers':'클리블랜드 캐벌리어스','Dallas Mavericks':'댈러스 매버릭스','Denver Nuggets':'덴버 너기츠','Detroit Pistons':'디트로이트 피스턴스','Golden State Warriors':'골든스테이트 워리어스','Houston Rockets':'휴스턴 로키츠','Indiana Pacers':'인디애나 페이서스','LA Clippers':'LA 클리퍼스','Los Angeles Clippers':'LA 클리퍼스','Los Angeles Lakers':'LA 레이커스','Memphis Grizzlies':'멤피스 그리즐리스','Miami Heat':'마이애미 히트','Milwaukee Bucks':'밀워키 벅스','Minnesota Timberwolves':'미네소타 팀버울브스','New Orleans Pelicans':'뉴올리언스 펠리컨스','New York Knicks':'뉴욕 닉스','Oklahoma City Thunder':'오클라호마시티 선더','Orlando Magic':'올랜도 매직','Philadelphia 76ers':'필라델피아 세븐티식서스','Phoenix Suns':'피닉스 선스','Portland Trail Blazers':'포틀랜드 트레일블레이저스','Sacramento Kings':'새크라멘토 킹스','San Antonio Spurs':'샌안토니오 스퍼스','Toronto Raptors':'토론토 랩터스','Utah Jazz':'유타 재즈','Washington Wizards':'워싱턴 위저즈','Macklin Celebrini':'맥클린 셀레브리니','Darnell Nurse':'다넬 너스','Igor Chernyshov':'이고르 체르니쇼프','Will Smith':'윌 스미스','Cole Caufield':'콜 코필드','Nick Suzuki':'닉 스즈키','Juraj Slafkovsky':'유라이 슬라프콥스키','Lane Hutson':'레인 허슨','Noah Dobson':'노아 돕슨','Jakub Dobes':'야쿠프 도베시','Alex Nedeljkovic':'알렉스 네델코비치','Artturi Lehkonen':'아르투리 레코넨','Nathan MacKinnon':'네이선 매키넌','Cale Makar':'케일 마카','Jack Hughes':'잭 휴스','Jesper Bratt':'예스페르 브라트','Luke Hughes':'루크 휴스','Brett Pesce':'브렛 페스체','Jake Allen':'제이크 앨런','Mohamed Diawara':'모하메드 디아와라','Kentavious Caldwell-Pope':'켄타비우스 콜드웰-폽','Jayson Tatum':'제이슨 테이텀'};
const leagueKo = {'Avispa Fukuoka':'아비스파 후쿠오카','Cerezo Osaka':'세레소 오사카','Fagiano Okayama':'파지아노 오카야마','FC Machida Zelvia':'FC 마치다 젤비아','FC Tokyo':'FC 도쿄','Gamba Osaka':'감바 오사카','JEF United Ichihara-Chiba':'제프 유나이티드 이치하라 지바','Kashiwa Reysol':'가시와 레이솔','Kashima Antlers':'가시마 앤틀러스','Kawasaki Frontale':'가와사키 프론탈레','Kyoto Sanga FC':'교토 상가 FC','Nagoya Grampus':'나고야 그램퍼스','Sanfrecce Hiroshima':'산프레체 히로시마','Shimizu S-Pulse':'시미즈 에스펄스','Shonan Bellmare':'쇼난 벨마레','Tokyo Verdy 1969':'도쿄 베르디','Urawa Red Diamonds':'우라와 레드 다이아몬즈','Vissel Kobe':'비셀 고베','Yokohama F. Marinos':'요코하마 F. 마리노스','Albirex Niigata':'알비렉스 니가타','Júbilo Iwata':'주빌로 이와타','Mito HollyHock':'미토 홀리호크','V-Varen Nagasaki':'V-파렌 나가사키','Hokkaido Consadole Sapporo':'홋카이도 콘사돌레 삿포로','Los Angeles Football Club':'로스앤젤레스 FC','Los Angeles FC':'로스앤젤레스 FC','Los Angeles Galaxy':'LA 갤럭시','Inter Miami CF':'인터 마이애미','Seattle Sounders FC':'시애틀 사운더스','Vancouver Whitecaps FC':'밴쿠버 화이트캡스','Portland Timbers':'포틀랜드 팀버스','New York City FC':'뉴욕 시티 FC','New York Red Bulls':'뉴욕 레드불스','New England Revolution':'뉴잉글랜드 레볼루션','Atlanta United FC':'애틀랜타 유나이티드','Austin FC':'오스틴 FC','Charlotte FC':'샬럿 FC','Chicago Fire FC':'시카고 파이어','Colorado Rapids':'콜로라도 래피즈','Columbus Crew':'콜럼버스 크루','FC Cincinnati':'FC 신시내티','FC Dallas':'FC 댈러스','Houston Dynamo FC':'휴스턴 다이너모','Minnesota United FC':'미네소타 유나이티드','Nashville SC':'내슈빌 SC','Orlando City SC':'올랜도 시티','Philadelphia Union':'필라델피아 유니언','Real Salt Lake':'레알 솔트레이크','San Diego FC':'샌디에이고 FC','San Jose Earthquakes':'산호세 어스퀘이크스','Sporting Kansas City':'스포팅 캔자스시티','St. Louis City SC':'세인트루이스 시티','Toronto FC':'토론토 FC','D.C. United':'DC 유나이티드','Washington Spirit':'워싱턴 스피릿','Indiana Fever':'인디애나 피버','Las Vegas Aces':'라스베이거스 에이시스','New York Liberty':'뉴욕 리버티','Phoenix Mercury':'피닉스 머큐리','Seattle Storm':'시애틀 스톰','Atlanta Dream':'애틀랜타 드림','Chicago Sky':'시카고 스카이','Connecticut Sun':'코네티컷 선','Dallas Wings':'댈러스 윙스','Golden State Valkyries':'골든스테이트 발키리스','Los Angeles Sparks':'LA 스파크스','Minnesota Lynx':'미네소타 링스','Portland Fire':'포틀랜드 파이어','Toronto Tempo':'토론토 템포','Washington Mystics':'워싱턴 미스틱스','Hanshin Tigers':'한신 타이거스','Yomiuri Giants':'요미우리 자이언츠','Yokohama DeNA BayStars':'요코하마 DeNA 베이스타스','Chunichi Dragons':'주니치 드래건스','Hiroshima Toyo Carp':'히로시마 도요 카프','Tokyo Yakult Swallows':'도쿄 야쿠르트 스왈로스','Fukuoka SoftBank Hawks':'후쿠오카 소프트뱅크 호크스','Hokkaido Nippon-Ham Fighters':'홋카이도 닛폰햄 파이터스','Chiba Lotte Marines':'지바 롯데 마린스','Tohoku Rakuten Golden Eagles':'도호쿠 라쿠텐 골든이글스','Saitama Seibu Lions':'사이타마 세이부 라이온스','Orix Buffaloes':'오릭스 버펄로스','中信兄弟':'중신 브라더스','統一獅':'통이 라이온스','樂天桃猿':'라쿠텐 몽키스','富邦悍將':'푸방 가디언스','味全龍':'웨이취안 드래곤스','台鋼雄鷹':'타이강 호크스','Anaheim Ducks':'애너하임 덕스','Boston Bruins':'보스턴 브루인스','Buffalo Sabres':'버펄로 세이버스','Calgary Flames':'캘거리 플레임스','Carolina Hurricanes':'캐롤라이나 허리케인스','Chicago Blackhawks':'시카고 블랙호크스','Colorado Avalanche':'콜로라도 애벌랜치','Columbus Blue Jackets':'콜럼버스 블루재킷스','Dallas Stars':'댈러스 스타스','Detroit Red Wings':'디트로이트 레드윙스','Edmonton Oilers':'에드먼턴 오일러스','Florida Panthers':'플로리다 팬서스','Los Angeles Kings':'로스앤젤레스 킹스','Minnesota Wild':'미네소타 와일드','Montreal Canadiens':'몬트리올 캐네이디언스','Nashville Predators':'내슈빌 프레데터스','New Jersey Devils':'뉴저지 데블스','New York Islanders':'뉴욕 아일랜더스','New York Rangers':'뉴욕 레인저스','Ottawa Senators':'오타와 세너터스','Philadelphia Flyers':'필라델피아 플라이어스','Pittsburgh Penguins':'피츠버그 펭귄스','San Jose Sharks':'산호세 샤크스','Seattle Kraken':'시애틀 크라켄','St. Louis Blues':'세인트루이스 블루스','Tampa Bay Lightning':'탬파베이 라이트닝','Toronto Maple Leafs':'토론토 메이플리프스','Utah Mammoth':'유타 매머스','Vancouver Canucks':'밴쿠버 커넉스','Vegas Golden Knights':'베이거스 골든나이츠','Washington Capitals':'워싱턴 캐피털스','Winnipeg Jets':'위니펙 제츠'};
const nhlPlayerKo = {
  'Nazem Kadri':'나젬 카드리','Scott Wedgewood':'스콧 웨지우드','Arseny Gritsyuk':'아르세니 그리추크','Michael Kesselring':'마이클 케셀링',
  'Alex Killorn':'알렉스 킬론','Leo Carlsson':'레오 칼손','Nikita Klepov':'니키타 클레포프','Jackson Lacombe':'잭슨 라콤브','Noah Warren':'노아 워런','Lukas Dostal':'루카시 도스탈','Simon Holmstrom':'시몬 홀름스트룀','Bo Horvat':'보 호바트','Kyle Palmieri':'카일 팔미에리','Logan Stanley':'로건 스탠리','Matthew Schaefer':'매슈 셰이퍼','Ilya Sorokin':'일리야 소로킨',
  'Artemi Panarin':'아르테미 파나린','Alex Laferriere':'알렉스 라페리에르','Adrian Kempe':'아드리안 켐페','Erik Gustafsson':'에리크 구스타프손','Brandt Clarke':'브랜트 클라크','Darcy Kuemper':'다르시 쿠엠퍼','Alex Tuch':'알렉스 터크','Dylan Strome':'딜런 스트롬','Jordan Kyrou':'조던 키루','Jakob Chychrun':'야코프 치크런','Matt Roy':'맷 로이','Logan Thompson':'로건 톰프슨',
  'Easton Cowan':'이스턴 코언','Auston Matthews':'오스턴 매슈스','Jack Roslovic':'잭 로슬로빅','Jake McCabe':'제이크 매케이브','Darren Raddysh':'대런 래디시','Anthony Stolarz':'앤서니 스톨라츠','Matthew Knies':'매슈 나이스','Adam Fantilli':'애덤 판틸리','Kent Johnson':'켄트 존슨','Zach Werenski':'잭 워런스키','Damon Severson':'데이먼 세버슨','Jet Greaves':'젯 그리브스',
  'Kyle Connor':'카일 코너','Mark Scheifele':'마크 샤이펄리','Cole Perfetti':'콜 퍼페티','Dylan Samberg':'딜런 샘버그','Neal Pionk':'닐 피언크','Stuart Skinner':'스튜어트 스키너','Dylan Holloway':'딜런 홀러웨이','Robert Thomas':'로버트 토머스','Jimmy Snuggerud':'지미 스너거루드','Philip Broberg':'필리프 브로베리','Justin Barron':'저스틴 배런','Joel Hofer':'조엘 호퍼',
  'JJ Peterka':'JJ 페테르카','Fraser Minten':'프레이저 민턴','David Pastrnak':'다비드 파스트르냐크','Hampus Lindholm':'함푸스 린드홀름','Charlie McAvoy':'찰리 매커보이','Jeremy Swayman':'제러미 스웨이먼','Sam Steel':'샘 스틸','Wyatt Johnston':'와이엇 존스턴','Mikko Rantanen':'미코 란타넨','Thomas Harley':'토머스 할리','Miro Heiskanen':'미로 헤이스카넨','Jake Oettinger':'제이크 외팅어',
  'Kirill Kaprizov':'키릴 카프리조프','Joel Eriksson Ek':'조엘 에릭손 에크','Matt Boldy':'맷 볼디','Quinn Hughes':'퀸 휴스','Jonas Brodin':'요나스 브로딘','Jesper Wallstedt':'예스페르 발스테트','Vasily Podkolzin':'바실리 포드콜진','Connor McDavid':'코너 맥데이비드','Leon Draisaitl':'레온 드라이자이틀','Mattias Ekholm':'마티아스 에크홀름','Evan Bouchard':'에번 부샤드','Devon Levi':'데번 리바이',
  'Viktor Arvidsson':'빅토르 아르비드손','Dylan Larkin':'딜런 라킨','Lucas Raymond':'루카스 레이먼드','Ben Chiarot':'벤 키아로','Moritz Seider':'모리츠 자이더','Daniil Tarasov':'다닐 타라소프','Jared McCann':'재러드 매캔','Matty Beniers':'매티 베니어스','Jordan Eberle':'조던 에벌리','Vince Dunn':'빈스 던','Adam Larsson':'아담 라르손','Joey Daccord':'조이 다코드',
  'Andrei Svechnikov':'안드레이 스베치니코프','Sebastian Aho':'세바스티안 아호','William Carrier':'윌리엄 카리에','Jaccob Slavin':'제이콥 슬레이빈','Jalen Chatfield':'제일런 채트필드','Pyotr Kochetkov':'표트르 코체트코프','Jake DeBrusk':'제이크 드브러스크','Elias Pettersson':'엘리아스 페테르손','Linus Karlsson':'리누스 칼손','Elias Nils Pettersson':'엘리아스 닐스 페테르손','Filip Hronek':'필리프 흐로네크','Leevi Merilainen':'레비 메릴라이넨',
  'Brandon Hagel':'브랜던 헤이글','Anthony Cirelli':'앤서니 시렐리','Nikita Kucherov':'니키타 쿠체로프','J.J. Moser':'JJ 모저','John Carlson':'존 칼슨','Dennis Hildeby':'데니스 힐데비','Ivan Barbashev':'이반 바르바셰프','Jack Eichel':'잭 아이켈','Mark Stone':'마크 스톤','Brayden McNabb':'브레이든 맥냅','Shea Theodore':'셰이 시어도어','Carter Hart':'카터 하트',
  'Trevor Zegras':'트레버 제그라스','Christian Dvorak':'크리스천 드보락','Noel Acciari':'노엘 아치아리','Travis Sanheim':'트래비스 샌하임','Oliver Bonk':'올리버 본크','Dan Vladar':'단 블라다르','Josh Doan':'조시 도안','Jiri Kulich':'이르지 쿨리치','Tage Thompson':'테이지 톰프슨','Mattias Samuelsson':'마티아스 새뮤얼손','Rasmus Dahlin':'라스무스 달린','Ukko-Pekka Luukkonen':'우코페카 루코넨',
  'Brady Tkachuk':'브래디 타카척','Sam Bennett':'샘 베넷','Matthew Tkachuk':'매슈 타카척','Gustav Forsling':'구스타프 포르슬링','Aaron Ekblad':'애런 에크블라드','Jacob Markstrom':'야코브 마르크스트룀','Warren Foegele':'워런 포겔','Tim Stützle':'팀 슈튀츨레','Claude Giroux':'클로드 지루','Jake Sanderson':'제이크 샌더슨','Artem Zub':'아르툠 주브','Linus Ullmark':'리누스 울마르크'
};
// Add Korean spellings after checking Google and Naver results against official club material; use Transfermarkt to confirm player identity. Unverified names stay English.
const naverKo = {...footballKo,...extraKo,...leagueKo,...nhlPlayerKo,...playerKo};
const normalizePlayerName = value => String(value||'').replace(/Ł/g,'L').replace(/ł/g,'l').normalize('NFD').replace(/[\u0300-\u036f]/g,'').normalize('NFC').replace(/[^\p{L}\p{N}]/gu,'').toLowerCase();
const naverKoNormalized = Object.fromEntries(Object.entries(naverKo).map(([name,korean])=>[normalizePlayerName(name),korean]));
const koreanPlayerNames = new Set([
  'Son Heung-min','Son Heung Min','Lee Kang-in','Lee Kang In','Kim Min-jae','Kim Min Jae','Hwang Hee-chan','Lee Jae-sung','Hwang Ui-jo','Cho Gue-sung','Jeong Woo-yeong','Jung Woo-young','Oh Hyeon-gyu','Paik Seung-ho','Seol Young-woo','Hong Hyun-seok','Bae Jun-ho','Yang Hyun-jun','Kwon Hyeok-kyu','Kim Ji-soo','Ji So-yun','Cho So-hyun','Casey Phair','Chun Ga-ram','Lee Geum-min','Jang Sel-gi','Kang Chae-rim','Son Hwa-yeon','Lee Min-a','Ryu Hyun-jin','Kim Ha-seong','Lee Jung-hoo','Kim Hye-seong','Choi Ji-man','Park Hyo-jun'
].map(normalizePlayerName));
function isKoreanPlayer(player) {
  if(['kbo','kbl','wkbl','kovo'].includes(sport) || (sport==='football' && ['kleague1','kleague2'].includes(league)))return false;
  const athlete=player?.athlete||player||{};
  const nationality=[athlete.nationality,athlete.citizenship,athlete.country,player?.nationality,player?.country].flat().map(value=>typeof value==='string'?value:value?.displayName||value?.name||value?.abbreviation||'').join(' ');
  if (/대한민국|한국|korea|\bkor\b/i.test(nationality)) return true;
  if (koreanPlayerNames.has(normalizePlayerName(player?.name))) return true;
  return false;
}
const projectionUrl = 'https://api.github.com/repos/jimmy896376/sports-lineups/contents/dist/projections.json?ref=main';
const codeAliases = {MCI:'MNC'};
let language = 'ko', sport = 'football', league = 'ucl', requestId = 0, majorView = true;
let theme = 'dark';
// Sandboxed board previews can block localStorage, including access to the getter.
try { theme = localStorage.getItem('sports-lineups-theme') || theme; } catch {}
document.documentElement.dataset.theme = theme;
const $ = id => document.getElementById(id);
const label = (en,ko) => ko;
const categoryForSport = value => categories.find(category => category.sports.includes(value));
const safe = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
let teamKo = {}, teamKoNormalized = {}, teamEnglish = {};
let nameReview = null;
function applyTeamNames(dictionary) {
  if (!dictionary || Array.isArray(dictionary) || typeof dictionary !== 'object' || !Object.keys(dictionary).length || Object.entries(dictionary).some(([name,korean])=>!name || typeof korean !== 'string' || korean.length>160 || !/\p{Script=Hangul}/u.test(korean))) throw new Error('Invalid team name dictionary');
  teamKo = dictionary;
  teamKoNormalized = Object.fromEntries(Object.entries(dictionary).map(([name,korean])=>[normalizePlayerName(name),korean]));
}
async function refreshTeamNames(current) {
  try {
    let remote, bundled;
    try {
      remote = await getJson(`https://raw.githubusercontent.com/jimmy896376/sports-lineups/main/dist/name-catalog.json?v=${Date.now()}`);
      if (remote?.schemaVersion !== 1) remote = null;
    } catch {}
    try {
      bundled = await getJson(`name-catalog.json?v=${Date.now()}`);
      if (bundled?.schemaVersion !== 1) bundled = null;
    } catch {}
    if (!remote && !bundled) throw new Error('Name catalog unavailable');
    // Prefer the newer catalog when GitHub's CDN temporarily serves an older snapshot.
    const [older, newer] = Date.parse(remote?.generatedAt || 0) > Date.parse(bundled?.generatedAt || 0)
      ? [bundled, remote] : [remote, bundled];
    const catalog = {
      teams: {...older?.teams,...newer?.teams},
      teamEnglish: {...older?.teamEnglish,...newer?.teamEnglish},
      players: {...older?.players,...newer?.players}
    };
    const dictionary = catalog.teams;
    const english = catalog.teamEnglish || {};
    if (Array.isArray(english) || typeof english !== 'object' || Object.entries(english).some(([name,full])=>!name || typeof full !== 'string' || !full || full.length>160)) throw new Error('Invalid full team name catalog');
    if (!catalog.players || Array.isArray(catalog.players) || typeof catalog.players !== 'object' || Object.entries(catalog.players).some(([name,korean])=>!name || typeof korean !== 'string' || korean.length>160 || !/\p{Script=Hangul}/u.test(korean))) throw new Error('Invalid player name catalog');
    if (current !== requestId) return;
    applyTeamNames(dictionary);
    teamEnglish = Object.fromEntries(Object.entries(english).map(([name,full])=>[normalizePlayerName(name),full]));
    Object.assign(naverKo,catalog.players);
    Object.assign(naverKoNormalized,Object.fromEntries(Object.entries(catalog.players).map(([name,korean])=>[normalizePlayerName(name),korean])));
    nameReview.dictionaryStatus = 'fresh';
    renderTeamSearch();
  } catch {
    if (current === requestId) nameReview.dictionaryStatus = 'unavailable';
  }
}
function auditName(kind,name,korean,reviewed) {
  if (nameReview && name) nameReview.names.set(kind+':'+name,{kind,name,korean,reviewed});
}
function teamDisplayName(team) {
  const name = team?.displayName || team?.name || '';
  const korean = teamKo[name] || teamKoNormalized[normalizePlayerName(name)];
  auditName('team',name,korean||name,Boolean(korean));
  if (language === 'en') return teamEnglish[normalizePlayerName(name)] || name;
  return korean || translated(name);
}
function playerDisplayName(name,shortName,lastName) {
  const korean = naverKo[name] || naverKoNormalized[normalizePlayerName(name)] || chinesePlayerKo[name] || naverKo[shortName] || naverKoNormalized[normalizePlayerName(shortName)];
  auditName('player',name,korean||name,Boolean(korean)||/\p{Script=Hangul}/u.test(name));
  return translated(name,shortName,lastName);
}
function finishNameReview(current) {
  if (current !== requestId || nameReview?.request !== current) return;
  const names = [...nameReview.names.values()];
  const report = {checkedAt:new Date().toISOString(),league:sport==='football'?league:sport,status:nameReview.failed?'data-unavailable':'checked',dictionaryStatus:nameReview.dictionaryStatus,names,pending:names.filter(row=>!row.reviewed)};
  // Browser-local report only; search verification still requires reviewed sources.
  try { localStorage.setItem('sports-lineups-name-review',JSON.stringify(report)); } catch {}
  nameReview = null;
}
const englishNames = {'中信兄弟':'CTBC Brothers','統一獅':'Uni-President Lions','樂天桃猿':'Rakuten Monkeys','富邦悍將':'Fubon Guardians','味全龍':'Wei Chuan Dragons','台鋼雄鷹':'TSG Hawks','張士綸':'Zhang Shilun','岳東華':'Yue Donghua','張仁瑋':'Zhang Renwei','曾頌恩':'Zeng Songen','陳俊秀':'Chen Junxiu','王政順':'Wang Zhengshun','王威晨':'Wang Weichen','江坤宇':'Jiang Kunyu','黃韋盛':'Huang Weisheng','李凱威':'Li Kaiwei','郭天信':'Guo Tianxin','張政禹':'Zhang Zhengyu','劉基鴻':'Liu Jihong','陳子豪':'Chen Zihao','朱育賢':'Zhu Yuxian','劉俊緯':'Liu Junwei','蔣少宏':'Jiang Shaohong','曾聖安':'Zeng Sheng An'};
const chinesePlayerKo = {'張士綸':'장스룬','岳東華':'위에둥화','張仁瑋':'장런웨이','曾頌恩':'쩡쑹언','陳俊秀':'천쥔슈','王政順':'왕정순','王威晨':'왕웨이천','江坤宇':'장쿤위','黃韋盛':'황웨이성','李凱威':'리카이웨이','郭天信':'궈톈신','張政禹':'장정위','劉基鴻':'류지훙','陳子豪':'천쯔하오','朱育賢':'주위셴','劉俊緯':'류쥔웨이','蔣少宏':'장샤오훙','曾聖安':'쩡성안'};
function romanizeHangul(value) {
  const initials=['g','kk','n','d','tt','r','m','b','pp','s','ss','','j','jj','ch','k','t','p','h'];
  const vowels=['a','ae','ya','yae','eo','e','yeo','ye','o','wa','wae','oe','yo','u','wo','we','wi','yu','eu','ui','i'];
  const finals=['','k','k','ks','n','nj','nh','t','l','lk','lm','lp','ls','lt','lp','lh','m','p','ps','t','t','ng','t','t','k','t','p','h'];
  return [...String(value || '')].map(char=>{const code=char.charCodeAt(0)-0xac00;if(code<0||code>11171)return char;const initial=Math.floor(code/588),vowel=Math.floor((code%588)/28),final=code%28;return initials[initial]+vowels[vowel]+finals[final]}).join('');
}
function hangulizeLatin(value) {
  const initial={g:'ㄱ',k:'ㅋ',c:'ㅋ',q:'ㅋ',d:'ㄷ',t:'ㅌ',b:'ㅂ',p:'ㅍ',f:'ㅍ',v:'ㅂ',m:'ㅁ',n:'ㄴ',r:'ㄹ',l:'ㄹ',s:'ㅅ',z:'ㅈ',j:'ㅈ',h:'ㅎ',w:'ㅇ',y:'ㅇ',x:'ㅋ'};
  const final={g:'ㄱ',k:'ㄱ',c:'ㄱ',q:'ㄱ',d:'ㄷ',t:'ㅅ',b:'ㅂ',p:'ㅂ',m:'ㅁ',n:'ㄴ',r:'ㄹ',l:'ㄹ',s:'ㅅ',z:'ㅅ',x:'ㄱ'};
  const vowels={a:'ㅏ',e:'ㅔ',i:'ㅣ',o:'ㅗ',u:'ㅜ',y:'ㅣ'};
  const clusters=[['tch','ch'],['sch','sh'],['sh','s'],['ch','c'],['th','s'],['ph','f'],['wh','w'],['ck','k'],['qu','kw'],['ee','i'],['ea','i'],['oo','u'],['ou','u'],['ow','aw'],['ai','e'],['ay','e'],['oi','o'],['oy','o'],['x','ks']];
  const initialIndex={'ㄱ':0,'ㄲ':1,'ㄴ':2,'ㄷ':3,'ㄸ':4,'ㄹ':5,'ㅁ':6,'ㅂ':7,'ㅃ':8,'ㅅ':9,'ㅆ':10,'ㅇ':11,'ㅈ':12,'ㅉ':13,'ㅊ':14,'ㅋ':15,'ㅌ':16,'ㅍ':17,'ㅎ':18};
  const vowelIndex={'ㅏ':0,'ㅐ':1,'ㅑ':2,'ㅒ':3,'ㅓ':4,'ㅔ':5,'ㅕ':6,'ㅖ':7,'ㅗ':8,'ㅘ':9,'ㅙ':10,'ㅚ':11,'ㅛ':12,'ㅜ':13,'ㅝ':14,'ㅞ':15,'ㅟ':16,'ㅠ':17,'ㅡ':18,'ㅢ':19,'ㅣ':20};
  const finalIndex={'ㄱ':1,'ㄴ':4,'ㄷ':7,'ㄹ':8,'ㅁ':16,'ㅂ':17,'ㅅ':19,'ㅇ':21};
  const compose=(a,v,b)=>String.fromCharCode(0xac00+((initialIndex[a]??11)*21+(vowelIndex[v]??20))*28+(finalIndex[b]||0));
  return String(value).normalize('NFD').replace(/[\u0300-\u036f]/g,'').replace(/[A-Za-z]+/g,word=>{
    let text=word.toLowerCase();
    for(const [from,to] of clusters) text=text.replaceAll(from,to);
    text=text.replace(/c(?=[eiy])/g,'s');
    if(text.length>3&&/[^aeiou]e$/.test(text)) text=text.slice(0,-1);
    const nuclei=[]; let pending='';
    for(const char of text){
      if(vowels[char]){nuclei.push({onset:pending,vowel:vowels[char],coda:''});pending='';}
      else if(initial[char]) pending+=char;
    }
    if(!nuclei.length) return [...word].map(char=>initial[char.toLowerCase()]?compose('ㅇ','ㅡ','')+compose(initial[char.toLowerCase()],'ㅣ',''):char).join('');
    for(let i=0;i<nuclei.length;i++){
      const run=nuclei[i].onset;
      if(!run) { nuclei[i].onset=''; continue; }
      if(i===0){nuclei[i].onset=run.length>1?run[0]:run.at(-1); if(run.length>1) nuclei[i].coda=final[run[0]]||'';}
      else if(run.length>1){
        const stopLiquid=run.length===2&&['k','p','t','b','g','d'].includes(run[0])&&['l','r'].includes(run[1]);
        nuclei[i-1].coda=stopLiquid||run==='rn'||run==='rs'?'':final[run[0]]||'';
        nuclei[i].onset=run.at(-1);
        if(stopLiquid) nuclei[i-1].insert=compose(initial[run[0]],'ㅡ','');
      }
      else nuclei[i].onset=run;
    }
    const tail=pending;
    let suffix='';
    if(tail){
      const last=nuclei.at(-1);
      if(tail==='r') suffix=compose('ㄹ','ㅡ','');
      else if(tail.length>1){last.coda=tail[0]==='r'?'':final[tail[0]]||'';suffix=[...tail.slice(1)].map(char=>compose(initial[char]||'ㅇ','ㅡ','')).join('');}
      else last.coda=final[tail[0]]||'';
    }
  return nuclei.map(part=>compose(initial[part.onset]||'ㅇ',part.vowel,part.coda)+(part.insert||'')).join('')+suffix;
  });
}
function translated(value, shortName, lastName) {
  const text=String(value || '');
  const koreanName=naverKo[text]||naverKoNormalized[normalizePlayerName(text)]||chinesePlayerKo[text]||naverKo[shortName]||naverKoNormalized[normalizePlayerName(shortName)];
  if (language === 'ko') return koreanName || text;
  return englishNames[text] || (/\p{Script=Hangul}/u.test(text) ? romanizeHangul(text) : /\p{Script=Latin}/u.test(text) ? text.normalize('NFD').replace(/\p{M}/gu,'') : text);
}
function injuryNames(prediction) {
  return ['away','home'].flatMap(side=>[...(prediction?.injuryDetails?.[side]||[]),...(prediction?.injuries?.[side]||[])].map(record=>typeof record==='string'?record:record?.name||record?.player||''));
}
function availability(value) {
  const flags={DTD:['DTD','출전 불투명'],OUT:['Out','결장'],IR:['IR','부상자 명단'],'IR-LT':['IR-LT','장기 부상자 명단'],GTD:['GTD','경기 직전 결정']};
  const match=flags[String(value||'').toUpperCase()];
  return match?label(...[match[0],match[1]]):value;
}
function injuryStatus(value) {
  const key=String(value||'').toLowerCase().replaceAll('_','-');
  const statuses={'out':['Out','결장'],'questionable':['Questionable','출전 불투명'],'ques':['Questionable','출전 불투명'],'doubtful':['Doubtful','출전 가능성 낮음'],'day-to-day':['Day-to-day','당일 결정'],'gtd':['GTD','경기 직전 결정'],'dtd':['DTD','출전 불투명'],'injured reserve':['Injured reserve','부상자 명단'],'ir':['IR','부상자 명단'],'ir-lt':['IR-LT','장기 부상자 명단'],'15-day-il':['15-day IL','15일 부상자 명단'],'60-day-il':['60-day IL','60일 부상자 명단'],'suspended':['Suspended','출장 정지']};
  const found=statuses[key];
  return found?label(...[found[0],found[1]]):value?translated(value):'';
}
function injuryTerm(value) {
  if (!value) return '';
  const key=String(value).toLowerCase().trim();
  const terms={ankle:['ankle','발목'],foot:['foot','발'],toe:['toe','발가락'],knee:['knee','무릎'],thigh:['thigh','허벅지'],hamstring:['hamstring','햄스트링'],calf:['calf','종아리'],achilles:['achilles','아킬레스건'],hip:['hip','고관절'],back:['back','허리'],shoulder:['shoulder','어깨'],elbow:['elbow','팔꿈치'],wrist:['wrist','손목'],hand:['hand','손'],arm:['arm','팔'],leg:['leg','다리'],head:['head','머리'],neck:['neck','목'],groin:['groin','사타구니'],left:['left','좌측'],right:['right','우측'],illness:['illness','질병'],'upper body':['upper body','상체'],'lower body':['lower body','하체'],strain:['strain','근육 긴장'],sprain:['sprain','염좌'],fracture:['fracture','골절'],tear:['tear','파열'],concussion:['concussion','뇌진탕'],surgery:['surgery','수술'],suspension:['suspension','징계'],undisclosed:['undisclosed','세부 정보 비공개'],unknown:['unknown','미상']};
  const found=terms[key];
  return found?label(...[found[0],found[1]]):language==='ko'?'기타':value;
}
function injuryPanel(prediction,event) {
  if (!prediction) return '';
  const competitors=event.competitions?.[0]?.competitors||[];
  const groups=[];
  for (const side of ['away','home']) {
    const team=competitors.find(item=>item.homeAway===side);
    let records=prediction.injuryDetails?.[side]||[];
    if (!records.length) records=(prediction.injuries?.[side]||[]).map(item=>typeof item==='string'?{name:item}:item);
    if (!records.length) continue;
    const rows=records.map(record=>{
      const name=typeof record==='string'?record:record.name||record.player||'';
      if (!name) return '';
      const status=injuryStatus(record.status||record.flag);
      const part=record.part||record.injury||record.location;
      const sideName=record.side?injuryTerm(record.side):'';
      const condition=record.condition||'';
      const anatomy=[sideName,part?injuryTerm(part):'',condition?injuryTerm(condition):''].filter(Boolean).join(' ');
      const details=[status,anatomy].filter(Boolean);
      if (record.returnDate) {
        const rawDate=String(record.returnDate);
        const date=new Date(/^\d{4}-\d{2}-\d{2}$/.test(rawDate)?rawDate+'T12:00:00Z':rawDate);
        if (!Number.isNaN(date.getTime())) details.push(label(`Est. return ${new Intl.DateTimeFormat('en-US',{month:'short',day:'numeric',year:'numeric',timeZone:'UTC'}).format(date)}`,`복귀 예상 ${new Intl.DateTimeFormat('ko-KR',{month:'long',day:'numeric',timeZone:'Asia/Seoul'}).format(date)}`));
      }
      if (language==='en'&&record.comment) details.push(record.comment);
      return `<li><strong>${safe(playerDisplayName(name))}</strong>${details.length?`<span>${safe(details.join(' · '))}</span>`:''}</li>`;
    }).filter(Boolean).join('');
    if (rows) groups.push(`<section><h4>${safe(teamDisplayName(team?.team))}</h4><ul>${rows}</ul></section>`);
  }
  return groups.length?`<details class="injury-box"><summary>${label('Injuries & availability','부상·출전 불투명')}</summary><div>${groups.join('')}</div></details>`:'';
}
function kst(iso) {
  const options = language === 'ko'
    ? {year:'numeric',month:'long',day:'numeric',weekday:'short',hour:'2-digit',minute:'2-digit',hour12:false,timeZone:'Asia/Seoul'}
    : {year:'numeric',month:'short',day:'numeric',weekday:'short',hour:'2-digit',minute:'2-digit',hour12:false,timeZone:'Asia/Seoul'};
  return new Intl.DateTimeFormat(language === 'ko' ? 'ko-KR' : 'en-US',options).format(new Date(iso));
}
function monthKeys() {
  const parts = new Intl.DateTimeFormat('en-CA',{timeZone:'Asia/Seoul',year:'numeric',month:'2-digit'}).formatToParts(new Date());
  const year = Number(parts.find(part => part.type === 'year').value);
  const month = Number(parts.find(part => part.type === 'month').value);
  return [-5,-4,-3,-2,-1,0,1].map(offset => {
    const date = new Date(Date.UTC(year,month-1+offset,1));
    return `${date.getUTCFullYear()}${String(date.getUTCMonth()+1).padStart(2,'0')}`;
  });
}
function kstDayRange() {
  const parts = new Intl.DateTimeFormat('en-CA',{timeZone:'Asia/Seoul',year:'numeric',month:'2-digit',day:'2-digit'}).formatToParts(new Date());
  const get = type => Number(parts.find(part => part.type === type).value);
  const start = Date.UTC(get('year'),get('month')-1,get('day')) - 9*3600000;
  return [start,start+2*24*3600000];
}
async function getJson(url) {
  const response = await fetch(url,{cache:'no-store'});
  if (!response.ok) throw new Error(`HTTP ${response.status}`);
  return response.json();
}
async function getProjections(preferFresh=false) {
  const fromApi = async () => {
    const response = await fetch(`${projectionUrl}&v=${Date.now()}`,{cache:'no-store',headers:{Accept:'application/vnd.github+json'}});
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const binary = atob((await response.json()).content.replace(/\s/g,''));
    return JSON.parse(new TextDecoder().decode(Uint8Array.from(binary,character => character.charCodeAt(0))));
  };
  const fromRaw = () => getJson(`https://raw.githubusercontent.com/jimmy896376/sports-lineups/main/dist/projections.json?v=${Date.now()}`);
  const valid = value => Array.isArray(value?.items) && value.domestic && typeof value.domestic === 'object';
  let projections;
  try {
    projections=await (preferFresh ? fromApi() : fromRaw());
    if(!valid(projections))throw new Error('Invalid lineup snapshot');
  } catch {
    projections=await (preferFresh ? fromRaw() : fromApi());
    if(!valid(projections))throw new Error('Invalid lineup snapshot');
  }
  indexTeamSearch(projections);
  return projections;
}
function projectionCheckedLabel(projections, key) {
  const source = projections.sourceStatus?.[key];
  const checked = source ? source.checkedAt : projections.asOf;
  return `${source?.fresh === false ? '자료원 갱신 실패 · 마지막 자료 ' : '자료 기준 '}${checked ? kst(checked) : '확인 불가'}`;
}
function starters(summary, event, kind) {
  const competition = event.competitions[0];
  const result = {};
  if (kind === 'football') {
    for (const roster of summary.rosters || []) {
      const players = (roster.roster || []).filter(player => player.starter);
      if (players.length === 11) result[roster.homeAway] = players.map(player => ({name:player.athlete.displayName,short:player.athlete.shortName,last:player.athlete.lastName,nationality:player.athlete.nationality,country:player.athlete.country}));
    }
  } else {
    for (const group of summary.boxscore?.players || []) {
      const competitor = competition.competitors.find(team => team.team.id === group.team.id);
      const stats = kind === 'mlb' ? group.statistics.filter(stat => stat.type === 'batting') : kind === 'nhl' ? group.statistics : group.statistics.slice(0,1);
      const players = stats.flatMap(stat => stat.athletes || []);
      const selected = players.filter(player => player.starter && (kind !== 'mlb' || player.batOrder > 0));
      const count = kind === 'mlb' ? 9 : kind === 'nhl' ? 6 : 5;
      if (competitor && selected.length === count) {
        if (kind === 'mlb') selected.sort((a,b) => a.batOrder-b.batOrder);
        if (kind === 'nhl') selected.sort((a,b) => Number(b.athlete.position?.abbreviation === 'G') - Number(a.athlete.position?.abbreviation === 'G'));
        result[competitor.homeAway] = selected.map(player => ({name:player.athlete.displayName,short:player.athlete.shortName,last:player.athlete.lastName,nationality:player.athlete.nationality,country:player.athlete.country}));
      }
    }
  }
  return result;
}
function hockeyRecentSix(summary,event,side) {
  const competitor=event.competitions?.[0]?.competitors?.find(team=>team.homeAway===side);
  const group=summary.boxscore?.players?.find(item=>item.team?.id===competitor?.team?.id);
  if (!group) return [];
  const rows=group.statistics.flatMap(stat=>(stat.athletes||[]).map(player=>({player,names:stat.names||[]})));
  const seconds=row=>{
    const index=row.names.findIndex(name=>/time.?on.?ice|toi/i.test(name));
    const raw=Array.isArray(row.player.stats)?row.player.stats[index]:row.player.stats?.timeOnIce;
    const match=String(raw||'').match(/^(\d+):(\d{2})$/);
    return match?Number(match[1])*60+Number(match[2]):0;
  };
  const isGoalie=row=>String(row.player.athlete?.position?.abbreviation||row.player.athlete?.position?.name||'').toLowerCase().match(/^(g|goalie|goaltender)$/);
  const active=rows.filter(row=>seconds(row)>0);
  const goalies=active.filter(isGoalie).sort((a,b)=>seconds(b)-seconds(a));
  const skaters=active.filter(row=>!isGoalie(row)).sort((a,b)=>seconds(b)-seconds(a));
  return [...goalies.slice(0,1),...skaters.slice(0,5)].map(({player})=>({name:player.athlete.displayName,short:player.athlete.shortName,last:player.athlete.lastName,nationality:player.athlete.nationality,country:player.athlete.country}));
}
function predictionFor(event, items, key) {
  const competitors = event.competitions[0].competitors;
  const away = competitors.find(team => team.homeAway === 'away');
  const home = competitors.find(team => team.homeAway === 'home');
  if (!away || !home) return null;
  const aliases={SJS:'SJ',NJD:'NJ',LAK:'LA',VGK:'VGK',...codeAliases};
  const code = value => aliases[value] || value;
  const normalize = value => String(value || '').toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g,'').replace(/[^a-z0-9]/g,'');
  const sameName = (a,b) => {
    const left=normalize(a),right=normalize(b);
    return Boolean(left && right && (left.includes(right) || right.includes(left)));
  };
  const found = items.map(item => {
    const timeWindow=key==='nhl'?12:2;
    if (item.league !== key || !Number.isFinite(Date.parse(item.kickoff)) || Math.abs(Date.parse(item.kickoff)-Date.parse(event.date)) >= timeWindow*3600000) return false;
    const normal = item.names?.away && item.names?.home && sameName(item.names.away,away.team.displayName) && sameName(item.names.home,home.team.displayName);
    const reversed = item.names?.away && item.names?.home && sameName(item.names.away,home.team.displayName) && sameName(item.names.home,away.team.displayName);
    const codesAvailable = item.teams?.away && item.teams?.home && away.team.abbreviation && home.team.abbreviation;
    const codesNormal = codesAvailable && code(item.teams.away) === code(away.team.abbreviation) && code(item.teams.home) === code(home.team.abbreviation);
    const codesReversed = codesAvailable && code(item.teams.away) === code(home.team.abbreviation) && code(item.teams.home) === code(away.team.abbreviation);
    if (normal || codesNormal) return item;
    return reversed || codesReversed ? {...item,
      lineups:{away:item.lineups?.home,home:item.lineups?.away},
      injuries:{away:item.injuries?.home,home:item.injuries?.away},
      injuryDetails:{away:item.injuryDetails?.home,home:item.injuryDetails?.away},
      startingPitchers:{away:item.startingPitchers?.home,home:item.startingPitchers?.away},
      statuses:{away:item.statuses?.home,home:item.statuses?.away}} : false;
  }).find(Boolean);
  return found || null;
}
function fillMissingLineups(existing={}, fallback={}) {
  return {away:existing.away?.length?existing.away:(fallback.away||[]),home:existing.home?.length?existing.home:(fallback.home||[])};
}
async function recentLineups(event, allEvents, source, kind) {
  const competitors = event.competitions[0].competitors;
  const expected = kind === 'football' ? 11 : kind === 'mlb' ? 9 : kind === 'nhl' ? 6 : 5;
  const lineups = {};
  for (const side of ['away','home']) {
    const target = competitors.find(team => team.homeAway === side);
    if (!target) continue;
    const past = allEvents.filter(candidate => Date.parse(candidate.date) < Date.parse(event.date) && candidate.status?.type?.completed && candidate.competitions?.[0]?.competitors?.some(team => team.team.id === target.team.id)).sort((a,b) => Date.parse(b.date)-Date.parse(a.date));
    for (const previous of past.slice(0,4)) {
      try {
        const summary = await getJson(`https://site.api.espn.com/apis/site/v2/sports/${source.path}/summary?event=${encodeURIComponent(previous.id)}`);
        const sideInPrevious = previous.competitions[0].competitors.find(team => team.team.id === target.team.id)?.homeAway;
        const found = kind === 'nhl' ? hockeyRecentSix(summary,previous,sideInPrevious) : starters(summary,previous,kind)[sideInPrevious];
        if (found?.length >= expected) { lineups[side] = found; break; }
      } catch {}
    }
  }
  return lineups;
}
const kblLogoCodes = {'원주 DB':'db','서울 삼성':'ss','서울 삼성 썬더스':'ss','고양 소노':'sono','서울 SK':'sk','창원 LG':'lg','창원 LG 세이커스':'lg','안양 정관장':'kgc','부산 KCC':'kcc','부산 KCC 이지스':'kcc','수원 KT':'kt','대구 한국가스공사':'pega','울산 현대모비스':'hd','울산 현대모비스 피버스':'hd'};
function teamLogo(team, className = 'team-logo') {
  const data = team?.team || team || {};
  const kblCode = sport === 'kbl' ? kblLogoCodes[data.displayName || data.name] : null;
  const url = data.logo || data.logos?.[0]?.href || team?.logo || team?.logos?.[0]?.href || (kblCode && `https://www.kbl.or.kr/assets/img/logo/logo-${kblCode}.svg`);
  return typeof url === 'string' && /^https:\/\//i.test(url)
    ? `<img class="${className}" src="${safe(url)}" alt="" aria-hidden="true" loading="lazy" onerror="this.hidden=true">`
    : '';
}
function baseballPitcher(team,prediction) {
  if(!['mlb','kbo','npb','cpbl'].includes(sport))return undefined;
  const announced=prediction?.startingPitchers?.[team.homeAway];
  if(announced?.name)return announced;
  const probable=(Array.isArray(team.probables)?team.probables:[]).find(row=>/^(probableStartingPitcher|startingPitcher)$/i.test(row.name||''));
  const athlete=probable?.athlete;
  if(athlete?.displayName || athlete?.fullName)return {name:athlete.displayName||athlete.fullName,short:athlete.shortName,last:athlete.lastName,status:'probable',nationality:athlete.nationality,country:athlete.country};
  return null;
}
function summaryPitchers(summary,event) {
  const result={};
  for(const group of summary.boxscore?.players||[]) {
    const competitor=event.competitions?.[0]?.competitors?.find(team=>String(team.team?.id)===String(group.team?.id));
    if(!competitor)continue;
    const starter=(group.statistics||[]).filter(stat=>stat.type==='pitching').flatMap(stat=>stat.athletes||[]).find(player=>player.starter===true);
    const athlete=starter?.athlete;
    if(athlete?.displayName)result[competitor.homeAway]={name:athlete.displayName,short:athlete.shortName,last:athlete.lastName,status:'confirmed',nationality:athlete.nationality,country:athlete.country};
  }
  return result;
}
function pitcherMarkup(pitcher) {
  if(pitcher===undefined)return '';
  if(!pitcher)return '<div class="starting-pitcher pending"><span>선발투수 예고 전</span></div>';
  return `<div class="starting-pitcher"><span>선발투수</span><strong>${safe(playerDisplayName(pitcher.name,pitcher.short,pitcher.last))}</strong><small>${pitcher.status==='confirmed'?'확정':'예고'}</small>${isKoreanPlayer(pitcher)?'<small class="korean-player">🇰🇷 한국</small>':''}</div>`;
}
function teamCard(team, players, pitcher) {
  const title = safe(teamDisplayName(team.team));
  const logo = teamLogo(team);
  const list = players?.length
    ? `<ol>${players.map(player => `<li>${safe(playerDisplayName(player.name,player.short,player.last))}${player.flag ? ` <small>${safe(availability(player.flag))}</small>` : ''}${isKoreanPlayer(player) ? ' <small class="korean-player" aria-label="대한민국 선수">🇰🇷 한국</small>' : ''}</li>`).join('')}</ol>`
    : '';
  const heading = team.homeAway === 'home' ? `<span>${title}</span>${logo}` : `${logo}<span>${title}</span>`;
  return `<div class="team"><h3 class="team-title">${heading}</h3>${pitcherMarkup(pitcher)}${list}</div>`;
}
function recentResults(team, event, events, side, prediction) {
  const supplied = event.recentForm?.[side] || prediction?.recentForm?.[side];
  if (Array.isArray(supplied) && supplied.length) return supplied.slice(-5);
  if (sport === 'football' && /^[WDL]{5}$/.test(team.form || '')) return [...team.form];
  const cutoff = Date.parse(event.date);
  return events.filter(candidate => Date.parse(candidate.date) < Math.min(cutoff,Date.now()) && candidate.status?.type?.completed).sort((a,b)=>Date.parse(a.date)-Date.parse(b.date))
    .map(candidate => {
      const opponent = candidate.competitions?.[0]?.competitors?.find(item => item.team?.id != null && team.team?.id != null && String(item.team.id) === String(team.team.id));
      if (!opponent) return null;
      const rivals = candidate.competitions[0].competitors;
      const other = rivals.find(item => item !== opponent);
      if (typeof opponent.winner === 'boolean') return opponent.winner ? 'W' : other?.winner ? 'L' : 'D';
      if(opponent.score == null || opponent.score === '' || other?.score == null || other.score === '')return null;
      const score = Number(opponent.score), otherScore = Number(other.score);
      if (!Number.isFinite(score) || !Number.isFinite(otherScore)) return null;
      return score > otherScore ? 'W' : score < otherScore ? 'L' : 'D';
    }).filter(Boolean).slice(-5);
}
function seasonRecordMarkup(team, side) {
  const records = team.records || team.team?.records || [];
  if (!Array.isArray(records)) return '';
  const summary = record => String(record?.summary || record?.displayValue || '');
  const valid = value => /^\d+\s*[-–]\s*\d+(?:\s*[-–]\s*\d+)?$/.test(value);
  const total = records.find(record => /overall|total|league/i.test(`${record.name || ''} ${record.type || ''}`) && valid(summary(record))) || records.find(record => /total/i.test(record.type || '') && valid(summary(record)));
  const venueName = side === 'home' ? /home/i : /away|road/i;
  const venue = records.find(record => venueName.test(`${record.name || ''} ${record.type || ''}`) && valid(summary(record)));
  if (!total && !venue) return '';
  const overallText = total ? `<span>시즌 ${safe(summary(total))}</span>` : '';
  const venueText = venue ? `<span>${side === 'home' ? '홈' : '원정'} ${safe(summary(venue))}</span>` : '';
  return `<span class="season-record" aria-label="시즌 및 ${side === 'home' ? '홈' : '원정'} 전적">${overallText}${venueText}</span>`;
}
function formMarkup(team, event, events, side, prediction) {
  const results = recentResults(team,event,events,side,prediction);
  const name = safe(teamDisplayName(team.team));
  const text = results.length ? results.map(result => `<span class="form-result ${result.toLowerCase()}" aria-label="${result === 'W' ? '승' : result === 'L' ? '패' : '무'}">${result === 'W' ? '승' : result === 'L' ? '패' : '무'}</span>`).join('') : '<span class="form-empty">결과 기록 없음</span>';
  const sportSupportsRecord = ['mlb','kbo','npb','cpbl','nba','wnba','ncaam','kbl','wkbl'].includes(sport);
  const record = sportSupportsRecord ? seasonRecordMarkup(team,side) : '';
  const logo = teamLogo(team,'matchup-logo');
  const location = `<small class="venue-tag ${side}">${side === 'home' ? '홈' : '원정'}</small>`;
  const heading = side === 'away' ? `${logo}<span>${name}</span>${location}` : `${location}<span>${name}</span>${logo}`;
  return `<div class="matchup-team ${side}"><div class="matchup-name">${heading}</div><div class="team-records"><span class="form-results" aria-label="최근 ${results.length}경기">${text}</span>${record}</div></div>`;
}
function predictionRecord(team,side,overall=false) {
  const records=team.records || team.team?.records || [];
  if(!Array.isArray(records))return null;
  const selector=overall?/overall|total|league/i:side==='home'?/home/i:/away|road/i;
  const record=records.find(row=>selector.test(`${row.name||''} ${row.type||''}`));
  if(!record)return null;
  const stats=Object.fromEntries((Array.isArray(record.stats)?record.stats:[]).map(item=>[item.name,Number(item.value)]));
  if(Number.isFinite(stats.wins)&&Number.isFinite(stats.losses))return {wins:stats.wins,losses:stats.losses,draws:stats.ties||stats.draws||0};
  // Soccer providers disagree on W-D-L/W-L-D summary order; use recent results instead.
  if(sport==='football')return null;
  const match=String(record.summary||record.displayValue||'').match(/^(\d+)\s*[-–]\s*(\d+)(?:\s*[-–]\s*(\d+))?$/);
  if(!match)return null;
  const third=Number(match[3]||0),hockey=['nhl','khl'].includes(sport);
  return {wins:Number(match[1]),losses:Number(match[2])+(hockey?third:0),draws:hockey?0:third};
}
let externalForecasts = {schemaVersion:1,items:[]};
async function refreshExternalForecasts(current) {
  let feed;
  try { feed=await getJson('https://raw.githubusercontent.com/jimmy896376/sports-lineups/main/dist/external-forecasts.json?v='+Date.now()); }
  catch { try { feed=await getJson('./external-forecasts.json?v='+Date.now()); } catch { feed={schemaVersion:1,items:[]}; } }
  if(current===requestId)externalForecasts=feed;
}
function outcomeMarkup(away,home,event,prediction,events) {
  const result=winProbability.external(externalForecasts,sport==='football'?league:sport,event);
  if(!result)return '';
  const rows=[{key:'away',label:'원정 승'},...(result.draw>0?[{key:'draw',label:'무승부'}]:[]),{key:'home',label:'홈 승'}];
  const values=rows.map(row=>`<div class="outcome-value ${row.key}"><span>${row.label}</span><strong>${result[row.key].toFixed(1)}<small>%</small></strong></div>`).join('');
  const bar=rows.map(row=>`<span class="${row.key}" style="width:${result[row.key]}%"></span>`).join('');
  return `<section class="outcome" aria-label="NUDE TV AI 승부예측 확률"><div class="outcome-heading"><strong>NUDE TV AI 승부예측</strong></div><div class="outcome-values" style="--outcome-columns:${rows.length}">${values}</div><div class="outcome-bar" aria-hidden="true">${bar}</div></section>`;
}
function gameCard(event, lineups, prediction, allEvents = []) {
  const competition = event.competitions[0];
  const away = competition.competitors.find(team => team.homeAway === 'away');
  const home = competition.competitors.find(team => team.homeAway === 'home');
  if (!away || !home) return '';
  const shown = {away:lineups.away?.length ? lineups.away : prediction?.lineups?.away || [],
    home:lineups.home?.length ? lineups.home : prediction?.lineups?.home || []};
  const confirmed = Boolean(shown.away.length && shown.home.length &&
    (lineups.away?.length || prediction?.statuses?.away === 'confirmed') &&
    (lineups.home?.length || prediction?.statuses?.home === 'confirmed'));
  const projected = !confirmed && Boolean(shown.away.length || shown.home.length);
  const lineupRows=Math.max(shown.away?.length||0,shown.home?.length||0,1);
  const teamRows=lineupRows+(['mlb','kbo','npb','cpbl'].includes(sport)?2:1);
  const statusText = confirmed ? label('Confirmed starters','확정 선발') : projected ? label('Projected lineup','예상 선발') : '';
  const statusClass = confirmed ? 'confirmed' : projected ? 'projected' : '';
  const key = sport === 'football' ? league : sport;
  return `<article class="card" data-home="${safe(home.team.displayName)}" data-away="${safe(away.team.displayName)}" tabindex="-1"><div class="card-top"><div class="match-info"><div class="time">${safe(kst(event.date))}</div><div class="matchup-grid">${formMarkup(away,event,allEvents,'away',prediction)}<span class="versus">VS</span>${formMarkup(home,event,allEvents,'home',prediction)}</div></div>${statusText ? `<span class="status ${statusClass}" role="status">${confirmed ? '✓ ' : ''}${statusText}</span>` : ''}</div>${outcomeMarkup(away,home,event,prediction,allEvents)}<div class="teams" style="--lineup-rows:${lineupRows};--team-rows:${teamRows}">${teamCard(away,shown.away,baseballPitcher(away,prediction))}${teamCard(home,shown.home,baseballPitcher(home,prediction))}</div>${injuryPanel(prediction,event)}</article>`;
}
let teamSearchRows = [];
const teamSearchKey = value => normalizePlayerName(value).replace(/\s/g,'');
const searchTeamName = name => language === 'ko' ? teamKo[name] || teamKoNormalized[normalizePlayerName(name)] || name : name;
function indexTeamSearch(projections,retain=false) {
  const [start,end] = kstDayRange();
  const rows = retain ? [...teamSearchRows] : [];
  for (const item of projections.items || []) {
    rows.push({league:item.league,date:item.kickoff,home:item.names?.home,away:item.names?.away,homeShort:item.teams?.home,awayShort:item.teams?.away});
  }
  for (const [key,entries] of Object.entries(projections.domestic || {})) {
    for (const {event} of entries) {
      const competitors=event?.competitions?.[0]?.competitors || [];
      const home=competitors.find(item=>item.homeAway==='home')?.team;
      const away=competitors.find(item=>item.homeAway==='away')?.team;
      rows.push({league:key,date:event?.date,home:home?.displayName,away:away?.displayName,homeShort:home?.abbreviation,awayShort:away?.abbreviation});
    }
  }
  teamSearchRows=[...new Map(rows.filter(row=>sources[row.league] && row.home && row.away && Date.parse(row.date)>=start && Date.parse(row.date)<end).map(row=>[`${row.league}:${Date.parse(row.date)}:${teamSearchKey(teamKoNormalized[normalizePlayerName(row.home)] || row.home)}:${teamSearchKey(teamKoNormalized[normalizePlayerName(row.away)] || row.away)}`,row])).values()].sort((a,b)=>Date.parse(a.date)-Date.parse(b.date));
  renderTeamSearch();
}
function findTeamGames(query) {
  const key=teamSearchKey(query);
  if(!key)return [];
  return teamSearchRows.map(row=>({row,score:Math.max(...['home','away'].map(side=>{
    const name=row[side],korean=teamKo[name] || teamKoNormalized[normalizePlayerName(name)];
    const aliases=korean ? Object.keys(teamKo).filter(alias=>teamKo[alias]===korean) : [];
    return Math.max(0,...[name,korean,row[side+'Short'],...aliases].filter(Boolean).map(value=>{
      const compact=teamSearchKey(value);
      if(compact===key)return 3;
      return compact.startsWith(key) || String(value).split(/\s+/).some(word=>teamSearchKey(word).startsWith(key)) ? 1 : 0;
    }));
  }))})).filter(item=>item.score>0).sort((a,b)=>b.score-a.score || Date.parse(a.row.date)-Date.parse(b.row.date)).map(item=>item.row);
}
function renderTeamSearch() {
  const query=($('team-search').value || '').trim();
  const results=$('team-search-results');
  results.hidden=!query;
  if(!query){results.innerHTML='';return;}
  const rows=findTeamGames(query);
  results.innerHTML=rows.length ? `<p class="search-summary">오늘·내일 경기 ${rows.length}개</p>`+rows.slice(0,20).map(row=>{
    const index=teamSearchRows.indexOf(row);
    return `<button type="button" class="team-search-result" data-search-game="${index}"><strong>${safe(searchTeamName(row.away))} <span class="search-vs">VS</span> ${safe(searchTeamName(row.home))}</strong><span>${safe(dropdownLeagueNames[row.league])} · ${safe(kst(row.date))}</span></button>`;
  }).join('') : `<p class="search-summary">${teamSearchRows.length ? '오늘·내일 조회된 경기에서 일치하는 팀이 없습니다.' : '경기 자료를 불러온 뒤 다시 검색해 주세요.'}</p>`;
}
async function openTeamSearchGame(index) {
  const row=teamSearchRows[index];
  if(!row)return;
  majorView=false;
  sport=leagueIds.includes(row.league)?'football':row.league;
  if(sport==='football')league=row.league;
  await loadGames();
  const card=[...document.querySelectorAll('.card[data-home]')].find(element=>element.dataset.home===row.home && element.dataset.away===row.away);
  if(card){card.classList.add('search-match');card.scrollIntoView({behavior:'smooth',block:'center'});card.focus({preventScroll:true});}
}

function showTabs() {
  const category = categoryForSport(sport);
  $('sports').innerHTML = `<button type="button" data-major="true" aria-current="${majorView}">주요 경기</button>`+categories.map(item => `<button type="button" data-category="${item.id}" aria-current="${!majorView && category.id === item.id}">${label(...item.label)}</button>`).join('');
  $('sport-menu').innerHTML = `<button type="button"><selectedcontent></selectedcontent></button><option value="major" ${majorView?'selected':''}><span class="menu-name major-menu-name">주요경기</span></option>`+categories.map(group => {
    const ids=dropdownLeagueOrder[group.id] || group.sports;
    const options=ids.map(id=>{
      const football=group.id==='football';
      const selected=!majorView && (football ? sport==='football' && league===id : sport===id);
      return `<option value="${football?'football:':''}${id}" ${selected?'selected':''}><span class="menu-icon">${safe(dropdownLeagueFlags[id])}</span> <span class="menu-name">${safe(dropdownLeagueLabel(id))}</span></option>`;
    });
    const [icon,...title]=label(...group.label).split(' ');
    return `<optgroup label="${label(...group.label)}"><legend><span class="menu-icon">${safe(icon)}</span> <span class="menu-name">${safe(title.join(' '))}</span></legend>${options.join('')}</optgroup>`;
  }).join('');
  const subSports = category.id === 'football' ? [] : category.sports.map(id => sports.find(item => item.id === id));
  const showSubnav = category.id === 'football' || category.id === 'volleyball' || subSports.length > 1;
  $('leagues').hidden = majorView || !showSubnav;
  $('leagues').setAttribute('aria-label',category.id === 'football' ? label('Football leagues','축구 대회') : label('Leagues','세부 리그'));
  $('leagues').innerHTML = category.id === 'football'
    ? leagueIds.map(id => leagueButton(id,sources[id],'data-league',league === id)).join('')
    : subSports.map(item => leagueButton(item.id,item,'data-sport',sport === item.id)).join('');
  $('brand').textContent = 'NUDE TV';
  $('site-name').textContent = label('Sports Lineups','스포츠 라인업');
  document.title = label('Sports Lineups','스포츠 라인업');
  document.querySelector('meta[name=description]').content = label('Sports league schedules and projected or confirmed lineups.','축구, 야구, 농구, 배구, 하키 리그의 경기 일정과 예상·확정 선발을 확인하세요.');
  $('language').textContent = language === 'ko' ? '영어' : '한국어';
  $('language').setAttribute('aria-pressed',String(language === 'en'));
  $('theme').textContent = theme === 'dark' ? label('☀️ Light mode','☀️ 화이트 모드') : label('🌙 Dark mode','🌙 다크 모드');
  $('theme').setAttribute('aria-pressed',String(theme === 'dark'));
  $('theme').setAttribute('aria-label',label('Switch color theme','화면 테마 변경'));
  $('refresh').textContent = label('Refresh','새로고침');
  $('sport-menu-title').textContent = label('Go to sport','종목 바로가기');
  $('notice').textContent = label('Game times are shown in Korea Standard Time. Keep this page open to refresh schedules and lineups every 5 minutes.','경기시간은 한국시간 기준으로 표시됩니다.\n페이지를 열어두시면, 경기일정과 라인업을 5분마다 갱신합니다.');
  document.documentElement.lang = language;
}
const majorLeagueIds=['nba','mlb','kbo','epl','ucl','uel','laliga','bundesliga','seriea','ligue1','kleague1','j1','kbl','wkbl','kovo','npb','cpbl','nhl'];
const majorLeaguePriority={ucl:70,epl:55,nba:55,kbo:65,mlb:50,laliga:45,bundesliga:40,seriea:40,ligue1:35,uel:45,kleague1:40,kbl:35,wkbl:25,kovo:35,npb:35,nhl:30,j1:25,cpbl:20};
const majorTeamPatterns={
  epl:/arsenal|chelsea|liverpool|manchester (?:city|united)|tottenham/i,
  laliga:/real madrid|barcelona|atl[eé]tico madrid/i,
  bundesliga:/bayern|dortmund|leverkusen/i,
  seriea:/inter(?: milan)?|juventus|ac milan|napoli/i,
  ligue1:/paris saint.germain|\bpsg\b/i,
  nba:/lakers|warriors|celtics|knicks|cavaliers|thunder/i,
  mlb:/dodgers|yankees|padres|mets|giants/i,
  kleague1:/울산|전북|서울|ulsan|jeonbuk|fc seoul/i
};
function majorGameScore(row) {
  const event=row.event,competition=event.competitions?.[0]||{};
  const names=(competition.competitors||[]).map(c=>c.team?.displayName||c.team?.name||'');
  const stage=[event.season?.slug,event.season?.name,competition.type?.text,competition.series?.title,...(competition.notes||[]).map(n=>n.headline),row.prediction?.competitionStage].filter(Boolean).join(' ');
  const postseason=event.season?.type===3 || /\bfinals?\b|playoffs?|postseason|world series|日本シリーズ|한국시리즈|결승|플레이오프|챔피언결정/i.test(stage);
  let score=majorLeaguePriority[row.key]||0;
  if(postseason)score+=150;
  const pattern=majorTeamPatterns[row.key];
  if(pattern)score+=names.filter(name=>pattern.test(name)).length*25;
  const competitors=competition.competitors||[];
  if(competitors.length===2 && competitors.every(c=>Number(c.curatedRank?.current)>0 && Number(c.curatedRank?.current)<=5))score+=25;
  const overseas=!['kbo','kbl','wkbl','kovo','kleague1','kleague2'].includes(row.key);
  const players=Object.values(row.prediction?.lineups||{}).flat();
  if(overseas && players.some(p=>koreanPlayerNames.has(normalizePlayerName(p.name||''))))score+=30;
  return score;
}
function majorGameRows(rows,start,end) {
  const seen=new Set(),counts=new Map();
  return rows.filter(({key,event})=>{
    const id=`${key}:${event.id}`;
    if(seen.has(id) || !event.id || event.status?.type?.completed || event.competitions?.[0]?.timeValid===false || !(Date.parse(event.date)>=start && Date.parse(event.date)<end))return false;
    seen.add(id);return true;
  }).map(row=>({row,score:majorGameScore(row)})).filter(x=>x.score>=65)
    .sort((a,b)=>b.score-a.score || Date.parse(a.row.event.date)-Date.parse(b.row.event.date))
    .filter(({row})=>{const count=counts.get(row.key)||0;counts.set(row.key,count+1);return count<3;})
    .slice(0,12).map(x=>x.row).sort((a,b)=>Date.parse(a.event.date)-Date.parse(b.event.date));
}
async function majorGameData(row,projections,history) {
  const kind=leagueIds.includes(row.key)?'football':row.key;
  const source=sources[row.key];
  let prediction=row.prediction || predictionFor(row.event,projections.items||[],row.key),lineups={};
  if(source.path) {
    const hours=(Date.parse(row.event.date)-Date.now())/3600000;
    if(hours<=(kind==='mlb'?8:3))try {
      const summary=await getJson(`https://site.api.espn.com/apis/site/v2/sports/${source.path}/summary?event=${encodeURIComponent(row.event.id)}`);
      lineups=starters(summary,row.event,kind);
      if(kind==='mlb')prediction={...prediction,startingPitchers:{...prediction?.startingPitchers,...summaryPitchers(summary,row.event)}};
    } catch {}
    if((!lineups.away?.length && !prediction?.lineups?.away?.length) || (!lineups.home?.length && !prediction?.lineups?.home?.length)) {
      const fallback=await recentLineups(row.event,history,source,kind);
      if(fallback.away?.length || fallback.home?.length)prediction={...prediction,lineups:fillMissingLineups(lineups,fillMissingLineups(prediction?.lineups,fallback)),statuses:{away:prediction?.statuses?.away||'predicted',home:prediction?.statuses?.home||'predicted'},note:prediction?.note||'최근 경기 선발 기준 예상'};
    }
  }
  return {...row,prediction,lineups};
}
async function loadMajorGames(current,preferFresh=false) {
  const [start,end]=kstDayRange();
  const first=new Date(start),previous=new Date(Date.UTC(first.getUTCFullYear(),first.getUTCMonth()-1,1));
  const months=[...new Set([previous,first,new Date(end-1)].map(date=>date.toISOString().slice(0,7).replace('-','')))];
  const jobs=majorLeagueIds.filter(key=>sources[key].path).flatMap(key=>months.map(month=>({key,url:`https://site.api.espn.com/apis/site/v2/sports/${sources[key].path}/scoreboard?dates=${month}&limit=500`})));
  const [scores,projections]=await Promise.all([Promise.allSettled(jobs.map(async job=>({key:job.key,data:await getJson(job.url)}))),getProjections(preferFresh).catch(()=>({items:[],domestic:{}}))]);
  if(current!==requestId)return;
  const rows=scores.filter(r=>r.status==='fulfilled').flatMap(r=>(r.value.data.events||[]).map(event=>({key:r.value.key,event})));
  for(const key of majorLeagueIds)for(const entry of projections.domestic?.[key]||[])rows.push({key,event:entry.event,prediction:entry.prediction});
  const allRows=[...new Map(rows.map(row=>[`${row.key}:${row.event.id}`,row])).values()];
  const rankedRows=allRows.map(row=>({...row,prediction:row.prediction||predictionFor(row.event,projections.items||[],row.key)}));
  const selected=majorGameRows(rankedRows,start,end);
  if(!scores.some(r=>r.status==='fulfilled') && !rows.length)nameReview.failed=true;
  indexTeamSearch({domestic:Object.fromEntries(majorLeagueIds.map(key=>[key,rows.filter(row=>row.key===key).map(row=>({event:row.event}))]))},true);
  const prepared=await Promise.all(selected.map(row=>majorGameData(row,projections,allRows.filter(r=>r.key===row.key).map(r=>r.event))));
  if(current!==requestId)return;
  // Reuse the existing league renderers synchronously after all requests complete.
  const previousSport=sport,previousLeague=league;
  try {
    const cards=prepared.map(row=>{
      sport=leagueIds.includes(row.key)?'football':row.key;
      if(sport==='football')league=row.key;
      const prediction=row.prediction;
      const card=gameCard(row.event,row.lineups||{},prediction,allRows.filter(r=>r.key===row.key).map(r=>r.event));
      return card.replace('tabindex="-1">',`tabindex="-1"><div class="overview-league">${safe(dropdownLeagueNames[row.key]||sources[row.key].label[1])}</div>`);
    });
    if(current===requestId){
      $('games').innerHTML=cards.length?`<div class="major-heading"><h2>오늘·내일 주요 경기</h2><p>결승·포스트시즌, 인기 리그·주요 팀 중심으로 선정 · 최대 12경기</p></div>`+cards.join(''):`<div class="empty">${scores.some(r=>r.status==='fulfilled')?'오늘·내일 선정 기준에 맞는 주요 경기가 없습니다. 전체 경기는 종목 메뉴에서 확인하세요.':'주요 경기 일정을 불러오지 못했습니다. 새로고침해 주세요.'}</div>`;
    }
  } finally {sport=previousSport;league=previousLeague;}
}
async function loadGames(preferFresh=true) {
  const current = ++requestId;
  nameReview = {request:current,names:new Map()};
  try {
  showTabs();
  $('games').innerHTML='<div class="empty">최신 경기 불러오는 중…</div>';
  await Promise.all([refreshTeamNames(current),refreshExternalForecasts(current)]);
  if (current !== requestId) return;
  if(majorView){await loadMajorGames(current,preferFresh);return;}
  const domesticKey = ['kbo','kbl','wkbl','kovo','khl','npb','cpbl'].includes(sport) ? sport : sport === 'football' && ['kleague1','kleague2'].includes(league) ? league : null;
  if (domesticKey) {
    const source = sources[domesticKey];
    $('games').innerHTML = `<div class="empty">${label('Loading latest schedule…','최신 경기 일정 불러오는 중…')}</div>`;
    try {
      const projections = await getProjections(preferFresh);
      if (current !== requestId) return;
      const [dayStart,dayEnd] = kstDayRange();
      const entries = projections.domestic?.[domesticKey] || [];
      const events = entries.filter(entry => Date.parse(entry.event.date) >= dayStart && Date.parse(entry.event.date) < dayEnd).sort((a,b) => Date.parse(a.event.date)-Date.parse(b.event.date));
      if (current !== requestId) return;
      $('games').innerHTML = events.length
        ? events.map(entry => { const confirmed = entry.prediction.statuses?.home === 'confirmed' && entry.prediction.statuses?.away === 'confirmed'; return gameCard(entry.event,confirmed ? entry.prediction.lineups || {} : {},entry.prediction,[]); }).join('')
        : `<div class="empty">${label('No scheduled games in this two-day period.','당일과 다음 날 예정된 경기가 없습니다.')}</div>`;
    } catch {
      if (current === requestId) nameReview.failed = true;
      if (current === requestId) $('games').innerHTML = `<div class="empty">${label('Schedule source could not be refreshed.','일정 자료원을 새로고침하지 못했습니다.')}</div>`;
    }
    return;
  }
  $('games').innerHTML = `<div class="empty">${label('Loading latest schedule…','최신 경기 일정 불러오는 중…')}</div>`;
  const source = sources[sport === 'football' ? league : sport];
  try {
    const [months, predictionsResult] = await Promise.all([
      Promise.allSettled(monthKeys().map(month => getJson(`https://site.api.espn.com/apis/site/v2/sports/${source.path}/scoreboard?dates=${month}&limit=500`))),
      getProjections(preferFresh).catch(() => ({asOf:null,items:[]}))
    ]);
    if (current !== requestId) return;
    const successful = months.filter(result => result.status === 'fulfilled');
    if (!successful.length) throw new Error('Schedule unavailable');
    const unique = new Map(successful.flatMap(result => result.value.events || []).map(event => [event.id,event]));
    const [dayStart,dayEnd] = kstDayRange();
    const allEvents = [...unique.values()];
    const events = allEvents.filter(event => !event.status?.type?.completed && event.competitions?.[0]?.timeValid !== false && Date.parse(event.date) >= dayStart && Date.parse(event.date) < dayEnd).sort((a,b) => Date.parse(a.date)-Date.parse(b.date));
    indexTeamSearch({domestic:{[sport==='football'?league:sport]:events.map(event=>({event}))}},true);
    if (!events.length) {
      $('games').innerHTML = `<div class="empty">${label('No scheduled games in this two-day period.','당일과 다음 날 예정된 경기가 없습니다.')}</div>`;
      return;
    }
    const kind = sport;
    const key = sport === 'football' ? league : sport;
    const predictionItems = predictionsResult.items || [];
    const cards = await Promise.all(events.map(async event => {
      const hours = (Date.parse(event.date)-Date.now())/3600000;
      let prediction = predictionFor(event,predictionItems,key);
      if (!prediction?.lineups?.away?.length || !prediction?.lineups?.home?.length) {
        const fallback = await recentLineups(event,allEvents,source,kind);
        if (fallback.away?.length || fallback.home?.length) prediction = {...(prediction || {}),league:key,kickoff:event.date,lineups:fillMissingLineups(prediction?.lineups,fallback),injuries:prediction?.injuries || {},statuses:{away:prediction?.statuses?.away||'predicted',home:prediction?.statuses?.home||'predicted'},note:prediction?.note||'최근 경기 선발 기준 예상'};
      }
      if (hours > (kind === 'mlb' ? 8 : 3)) return {event,lineups:{},prediction};
      try {
        const summary = await getJson(`https://site.api.espn.com/apis/site/v2/sports/${source.path}/summary?event=${encodeURIComponent(event.id)}`);
        return {event,lineups:starters(summary,event,kind),prediction:kind==='mlb'?{...prediction,startingPitchers:{...prediction?.startingPitchers,...summaryPitchers(summary,event)}}:prediction};
      } catch { return {event,lineups:{},prediction}; }
    }));
    if (current === requestId) $('games').innerHTML = cards.map(card=>gameCard(card.event,card.lineups,card.prediction,allEvents)).join('');
  } catch {
    if (current === requestId) nameReview.failed = true;
    if (current === requestId) $('games').innerHTML = `<div class="empty">${label('Schedule could not be loaded.','경기 일정을 불러오지 못했습니다.')}</div>`;
  }
  } finally { finishNameReview(current); }
}
$('leagues').addEventListener('error',event => { const image=event.target; if (image instanceof HTMLImageElement && image.classList.contains('league-logo')) { image.hidden=true; if (image.nextElementSibling) image.nextElementSibling.hidden=false; } },true);
$('sports').addEventListener('click',event => { const button=event.target.closest('[data-major],[data-category]'); if(!button)return; if(button.dataset.major){majorView=true;}else{majorView=false;const category=categories.find(item=>item.id===button.dataset.category);if(!category.sports.includes(sport))sport=category.sports[0];}loadGames(); });
$('sport-menu').addEventListener('change',event => {
  if(event.target.value==='major'){majorView=true;loadGames();return;}
  const [nextSport,nextLeague] = event.target.value.split(':');
  if (!sports.some(item => item.id === nextSport)) return;
  if (nextSport === 'football' && !leagueIds.includes(nextLeague)) return;
  majorView=false;
  sport=nextSport;
  if (nextLeague) league=nextLeague;
  loadGames();
});
$('leagues').addEventListener('click',event => { const button=event.target.closest('[data-league],[data-sport]'); if (button?.dataset.league) { majorView=false; league=button.dataset.league; loadGames(); } else if (button?.dataset.sport) { majorView=false; sport=button.dataset.sport; loadGames(); } });
$('language').addEventListener('click',() => { language=language === 'ko' ? 'en' : 'ko'; loadGames(); });
$('theme').addEventListener('click',() => { theme=theme === 'dark' ? 'light' : 'dark'; document.documentElement.dataset.theme=theme; try { localStorage.setItem('sports-lineups-theme',theme); } catch {} showTabs(); });
$('refresh').addEventListener('click',()=>loadGames(true));
$('team-search').addEventListener('input',renderTeamSearch);
$('team-search-results').addEventListener('click',event=>{const button=event.target.closest('[data-search-game]');if(button)openTeamSearchGame(Number(button.dataset.searchGame));});
document.addEventListener('visibilitychange',() => { if (document.visibilityState === 'visible') loadGames(); });
window.setInterval(() => { if (document.visibilityState === 'visible') loadGames(); },5*60*1000);
loadGames();
