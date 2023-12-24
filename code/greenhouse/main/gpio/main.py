#! /usr/bin/env python3
import json
import subprocess

def run_shell(cmd):
    out = ""
    err = ""

    try:
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True)
        (out, err) = p.communicate()
    except Exception as e:
        print(f"Error while running command {cmd}: {e}")

    if out:
        return out.decode("utf-8")
    else:
        return ""

def get_gpio_funcs():
  items = run_shell('raspi-gpio funcs').split('\n')
  titles = [item.strip().lower().replace(' ','_') for item in items[0].split(',')]
  result = []
  for item in items[1:]:
      di = {}
      gpio_data = [it.strip() for it in item.split(',')]
      res = list(zip(titles, gpio_data))
      if res[0][1] == '':
        continue
      for it in res:
        if it[1] == '-':
          continue
        if it[0] == 'GPIO':
          di['name'] = f'{it[0]} {it[1]}'
          di['gpio_number'] = int(it[1])
        else:
          di[it[0]] = it[1]
      result.append(di)
  return result


def get_gpio_states():
  items = run_shell('raspi-gpio get').split('\n')
  result =  []
  for item in items:
    if 'BANK' in item:
      splits = item.split(' ')
      bank_name = splits[0]
      bank_start = int(splits[2])
      bank_end = int(splits[4].replace(')','').replace(':',''))
      result.append({'bank_name': bank_name, 'bank_start': bank_start, 'bank_end': bank_end, 'gpio_ports': []})
      continue
    if item == '':
      continue
    data = item.split(':')
    gpio_name = data[0].strip()
    gpio_number = int(gpio_name.split(' ')[1])
    di = {'name': gpio_name, 'gpio_number': gpio_number}
    for metric in data[1].split(' '):
      arr = metric.split('=')
      if len(arr) == 1:
        continue
      k,v = tuple(arr)
      di[k]=v
    bank = [x for x in result if di['gpio_number'] >= x['bank_start'] and di['gpio_number'] <= x['bank_end']][0]
    bank['gpio_ports'].append(di)
  return result


def get_cpu_info():
  with open("/proc/cpuinfo", "r") as f:
    data = f.read().split('\n\n')
  result = []
  for item in data:
    item_data = item.split("\n")
    title = item_data[0].replace('\t','').split(':')
    di = {'type': title[0], 'value': title[1].strip()}
    for dat in item_data[1:]:
      it = dat.replace('\t','').split(':')
      if it[0] == '':
        continue
      di[it[0]] = it[1].strip()
    result.append(di)
  return result


if __name__ == "__main__":
  bank = [x for x in get_gpio_states() if x['bank_name']=='BANK0'][0]
  print(json.dumps(bank['gpio_ports'],indent=4))
