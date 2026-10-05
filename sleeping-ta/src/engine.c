#define _POSIX_C_SOURCE 200809L
#include <pthread.h>
#include <semaphore.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <errno.h>
#define MAX 40
/* Public API is called by one controller thread. Shared model uses mu. */
static pthread_mutex_t mu=PTHREAD_MUTEX_INITIALIZER;
static sem_t work, ta_tick, ack, started, ticks[MAX], done[MAX];
static pthread_t ta, students[MAX];
static int n,chairs,lo,hi,slo,shi,active,stop,now,current,q[MAX],qn,remaining;
static int state[MAX],due[MAX],visits[MAX],joined[MAX],rejected,completed,arrivals,busy,wait_sum;
static uint32_t rng;
static char events[262144]; static size_t used;
static void waitsem(sem_t *s){while(sem_wait(s)<0 && errno==EINTR){}}
static int random_between(int a,int b){rng=rng*1664525u+1013904223u;return a+(int)(rng%(unsigned)(b-a+1));}
static void event(const char *kind,int id){if(used<sizeof(events)-100)used+=(size_t)snprintf(events+used,sizeof(events)-used,"%d,%s,%d,%d\n",now,kind,id+1,qn);}
static void begin(int id){current=id;state[id]=2;remaining=random_between(slo,shi);wait_sum+=now-joined[id];event("help_start",id);}
static void *teacher(void *unused){(void)unused;
 for(;;){waitsem(&work);pthread_mutex_lock(&mu);if(stop){pthread_mutex_unlock(&mu);break;}begin(current);pthread_mutex_unlock(&mu);sem_post(&started);
  for(;;){waitsem(&ta_tick);pthread_mutex_lock(&mu);if(stop){pthread_mutex_unlock(&mu);return NULL;}busy++;remaining--;
   if(!remaining){int id=current;completed++;visits[id]++;state[id]=3;event("help_end",id);sem_post(&done[id]);
    if(qn){int next=q[0];memmove(q,q+1,(size_t)(--qn)*sizeof(int));begin(next);}else{current=-1;event("sleep",-1);}}
   int idle=current<0;pthread_mutex_unlock(&mu);sem_post(&ack);if(idle)break;
  }
 }return NULL;
}
static void *student(void *arg){int id=(int)(intptr_t)arg;
 for(;;){waitsem(&ticks[id]);pthread_mutex_lock(&mu);if(stop){pthread_mutex_unlock(&mu);break;}
  int wake=0;
  if(state[id]==3 && sem_trywait(&done[id])==0){state[id]=0;due[id]=now+random_between(lo,hi);event("program",id);}
  if(state[id]==0 && now>=due[id]){arrivals++;event("arrive",id);
   if(current<0){current=id;joined[id]=now;wake=1;sem_post(&work);}
   else if(qn<chairs){q[qn++]=id;state[id]=1;joined[id]=now;event("queue",id);}
   else{rejected++;due[id]=now+random_between(lo,hi);event("full_return",id);}}
  pthread_mutex_unlock(&mu);if(wake)waitsem(&started);sem_post(&ack);
 }return NULL;
}
void sim_close(void){if(!active)return;pthread_mutex_lock(&mu);stop=1;pthread_mutex_unlock(&mu);sem_post(&work);sem_post(&ta_tick);for(int i=0;i<n;i++)sem_post(&ticks[i]);pthread_join(ta,NULL);for(int i=0;i<n;i++)pthread_join(students[i],NULL);sem_destroy(&work);sem_destroy(&ta_tick);sem_destroy(&ack);sem_destroy(&started);for(int i=0;i<n;i++){sem_destroy(&ticks[i]);sem_destroy(&done[i]);}active=0;}
int sim_init(int count,int seats,int amin,int amax,int hmin,int hmax,unsigned seed){
 if(count<1||count>MAX||seats<0||seats>20||amin<1||amax<amin||amax>6000||hmin<1||hmax<hmin||hmax>6000)return -1;
 sim_close();n=count;chairs=seats;lo=amin;hi=amax;slo=hmin;shi=hmax;rng=seed;stop=now=qn=rejected=completed=arrivals=busy=wait_sum=0;current=-1;remaining=0;used=0;events[0]=0;memset(state,0,sizeof(state));memset(visits,0,sizeof(visits));
 if(sem_init(&work,0,0)||sem_init(&ta_tick,0,0)||sem_init(&ack,0,0)||sem_init(&started,0,0)){perror("sem_init");abort();}
 for(int i=0;i<n;i++){if(sem_init(&ticks[i],0,0)||sem_init(&done[i],0,0)){perror("sem_init");abort();}due[i]=random_between(lo,hi);}
 if(pthread_create(&ta,NULL,teacher,NULL)){fprintf(stderr,"TA thread creation failed\n");abort();}
 for(int i=0;i<n;i++)if(pthread_create(&students[i],NULL,student,(void *)(intptr_t)i)){fprintf(stderr,"Student thread creation failed\n");abort();}
 active=1;event("sleep",-1);return 0;
}
void sim_step(void){if(!active)return;pthread_mutex_lock(&mu);now++;int serving=current>=0;pthread_mutex_unlock(&mu);
 if(serving){sem_post(&ta_tick);waitsem(&ack);} /* finish service before arrivals */
 for(int k=0;k<n;k++){int i=(k+now)%n;sem_post(&ticks[i]);waitsem(&ack);}
}
const char *sim_snapshot(void){static char out[8192];pthread_mutex_lock(&mu);int p=snprintf(out,sizeof(out),"{\"tick\":%d,\"current\":%d,\"remaining\":%d,\"arrivals\":%d,\"rejected\":%d,\"completed\":%d,\"busy\":%d,\"wait_sum\":%d,\"queue\":[",now,current,remaining,arrivals,rejected,completed,busy,wait_sum);
 for(int i=0;i<qn;i++)p+=snprintf(out+p,sizeof(out)-(size_t)p,"%s%d",i?",":"",q[i]);
 p+=snprintf(out+p,sizeof(out)-(size_t)p,"],\"students\":[");
 for(int i=0;i<n;i++)p+=snprintf(out+p,sizeof(out)-(size_t)p,"%s{\"state\":%d,\"visits\":%d}",i?",":"",state[i],visits[i]);
 snprintf(out+p,sizeof(out)-(size_t)p,"]}");pthread_mutex_unlock(&mu);return out;}
const char *sim_events(void){return events;} /* controller calls only between steps */
