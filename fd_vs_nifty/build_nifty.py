import csv,glob,sys,datetime as dt
upl,eod,out=sys.argv[1:4]
user={}
for f in sorted(glob.glob(upl+'/*NIFTY_50_Historical_PR_*.csv')):
    for r in csv.DictReader(open(f,encoding='utf-8-sig')):
        d=dt.datetime.strptime(r['Date'],'%d %b %Y').date()
        user[d]=float(r['Close'])
e={}
for r in csv.DictReader(open(eod)):
    e[dt.date.fromisoformat(r['Date'])]=float(r['Close'])
both=sorted(set(user)&set(e))
bad=[(d,user[d],e[d]) for d in both if abs(user[d]-e[d])>0.01]
print('user days',len(user),'eod days',len(e),'overlap',len(both),'mismatch',len(bad))
for b in bad[:10]: print(b)
m=dict(e); m.update(user)
w=csv.writer(open(out,'w',newline='')); w.writerow(['date','close'])
for d in sorted(m): w.writerow([d.isoformat(),m[d]])
ys=sorted({d.year for d in m}); print('years',ys[0],'-',ys[-1],'missing years',[y for y in range(ys[0],ys[-1]+1) if y not in ys])