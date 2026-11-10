(async () => {
  const root = document.getElementById('calendar-events');
  const status = document.getElementById('calendar-status');
  const select = document.getElementById('calendar-period');
  if (!root || !status || !select) return;
  const today = new Intl.DateTimeFormat('sv-SE', {timeZone:'Asia/Bangkok'}).format(new Date());
  const dayLabel = value => new Intl.DateTimeFormat('vi-VN', {weekday:'long',day:'2-digit',month:'2-digit',year:'numeric',timeZone:'Asia/Bangkok'}).format(new Date(value+'T12:00:00+07:00'));
  try {
    const response = await fetch('calendar.json', {cache:'no-store'});
    if (!response.ok) throw Error('unavailable');
    const data = await response.json();
    if (!Array.isArray(data.events) || !Number.isFinite(Date.parse(data.updatedAt))) throw Error('invalid');
    const events = data.events.filter(e => e && /^\d{4}-\d{2}-\d{2}$/.test(e.date) && typeof e.content === 'string');
    const updated = new Date(data.updatedAt);
    const stamp = new Intl.DateTimeFormat('vi-VN', {dateStyle:'short',timeStyle:'short',timeZone:'Asia/Bangkok'}).format(updated);
    const stale = Date.now() - updated.getTime() > 24*60*60*1000;
    status.textContent = 'Cập nhật gần nhất: '+stamp+' (giờ Việt Nam).'+(stale?' Dữ liệu đã quá 24 giờ; vui lòng đối chiếu lịch gốc.':'');
    status.classList.toggle('calendar-stale', stale);
    function render() {
      root.replaceChildren();
      const start = new Date(today+'T12:00:00+07:00');
      const weekday = start.getUTCDay();
      start.setUTCDate(start.getUTCDate()-((weekday+6)%7));
      const monday = start.toISOString().slice(0,10);
      start.setUTCDate(start.getUTCDate()+6);
      const sunday = start.toISOString().slice(0,10);
      const visible = events.filter(e => select.value==='all' || (select.value==='today'?e.date===today:select.value==='week'?e.date>=monday&&e.date<=sunday:e.date>=today));
      if (!visible.length) {
        const empty = document.createElement('p');
        empty.textContent = 'Bản lịch đã đồng bộ chưa có công việc trong khoảng thời gian này. Bạn có thể chọn “Toàn bộ lịch đã đồng bộ” hoặc kiểm tra lịch gốc.';
        root.append(empty);return;
      }
      let date = '', group;
      for (const event of visible) {
        if (event.date!==date) {
          date=event.date;group=document.createElement('div');group.className='calendar-day';
          const heading=document.createElement('h3');heading.textContent=dayLabel(date)+(date===today?' · Hôm nay':'');group.append(heading);root.append(group);
        }
        const article=document.createElement('article');article.className='calendar-event';
        const heading=document.createElement('h4');heading.textContent=[event.time,event.content].filter(Boolean).join(' · ');article.append(heading);
        for(const [key,label] of [['chair','Chủ trì'],['participants','Thành phần'],['location','Địa điểm'],['transport','Phương tiện']]) {
          if(typeof event[key]==='string'&&event[key].trim()) {
            const p=document.createElement('p'),strong=document.createElement('strong');strong.textContent=label+': ';p.append(strong,document.createTextNode(event[key]));article.append(p);
          }
        }
        group.append(article);
      }
    }
    select.disabled=false;select.addEventListener('change',render);render();
  } catch {
    status.textContent='Chưa tải được bản lịch đồng bộ. Vui lòng mở lịch gốc để xem thông tin.';
    root.replaceChildren();
  }
})();