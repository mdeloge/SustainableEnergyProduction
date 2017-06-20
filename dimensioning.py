import matplotlib
import numpy as np
import matplotlib.pyplot as plt
import pandas
from matplotlib.externals import six
import mpld3
import copy

avg_cons = 23260  #Avg gas consumption in kWh for 1 family: 2 parents and 1 child
df = pandas.read_csv("gas_vreg.csv")
df = df.drop(['year','Month','Day','h','From','To'], 1)
df['cons_kWh'] = df.apply(lambda row: row['Cons_percentage']*avg_cons*5, axis=1)

CHP_one = 20000
CHP_two = 20000
generator_power = 5000  #Power in Wh/h
buffer_size = 3000   #buffer size in liters
max_buffer_energy = buffer_size*4.2*20/3.6 #Energy stored in full buffer 
#4.2 caloric value water, 20 = delta t, 3.6 is Joule to Watt conversion factor
buffer_energy = 0
prev_CHP_val_one = 0
prev_CHP_val_two = 0
data_CHP_dual = df

for index, row in data_CHP_dual.iterrows():
    demand = row['cons_kWh']*1000     #times 1000 for conversion to Wh
    waste_energy = 0
    if demand <= generator_power:       #CHP unit is not turned on
        excess_heat = generator_power - demand
        buffer_energy += excess_heat
        if buffer_energy > max_buffer_energy:
            waste_energy = buffer_energy - max_buffer_energy
            buffer_energy = max_buffer_energy
   
        data_CHP_dual.set_value(index, 'CHP_prod_one', 0)
        data_CHP_dual.set_value(index, 'CHP_prod_two', 0)
        prev_CHP_val_one = 0
        prev_CHP_val_two = 0
    else:
        #extra heat needs to be provided, either by buffer, CHP units or both
        #1: buffer can provide enough energy to supply demand        
        #2: buffer can't provide enough
            #2.1: one CHP unit is added to the mix, excess heat stored in buffer            
            #2.2: two CHP or more units are needed            
            #2.3: all CHP units are working but demand couldn't be supplied
        extra_needed = demand - generator_power
        if extra_needed <= buffer_energy:
            buffer_energy -= extra_needed  
            if buffer_energy<max_buffer_energy - CHP_one and prev_CHP_val_one>0:
                #since CHP unit was turned on anyway we're going to let it run 
                #a bit longer to fill the buffer
                data_CHP_dual.set_value(index, 'CHP_prod_one', CHP_one)
                buffer_energy += CHP_one
                data_CHP_dual.set_value(index, 'CHP_prod_two', 0)
                prev_CHP_val_one = CHP_one
                prev_CHP_val_two = 0
            else:            
                data_CHP_dual.set_value(index, 'CHP_prod_one', 0)
                data_CHP_dual.set_value(index, 'CHP_prod_two', 0)
                prev_CHP_val_one = 0
                prev_CHP_val_two = 0
        else: #buffer alone can't supply the nescessary extra heat 
            extra_needed -= buffer_energy
            buffer_energy = 0
            
            if extra_needed <= CHP_one:
                excess_heat = CHP_one - extra_needed
                data_CHP_dual.set_value(index, 'CHP_prod_one', CHP_one)
                data_CHP_dual.set_value(index, 'CHP_prod_two', 0)
                prev_CHP_val_one = CHP_one
                prev_CHP_val_two = 0
                #store excess heat in the buffer
                buffer_energy += excess_heat
                if buffer_energy > max_buffer_energy:
                    waste_energy = buffer_energy - max_buffer_energy
                    buffer_energy = max_buffer_energy
            elif extra_needed > CHP_one and extra_needed <= CHP_one + CHP_two:
                excess_heat = CHP_one + CHP_two - extra_needed
                data_CHP_dual.set_value(index, 'CHP_prod_one', CHP_one)
                data_CHP_dual.set_value(index, 'CHP_prod_two', CHP_two)
                prev_CHP_val_one = CHP_one
                prev_CHP_val_two = CHP_two
                #store excess heat in the buffer
                buffer_energy += excess_heat
                if buffer_energy > max_buffer_energy:
                    waste_energy = buffer_energy - max_buffer_energy
                    buffer_energy = max_buffer_energy
            else:
                print "CHP unit can't supply sufficient energy at: ", row['UTC']
                data_CHP_dual.set_value(index, 'CHP_prod_one', CHP_one)
                data_CHP_dual.set_value(index, 'CHP_prod_two', CHP_two)
                prev_CHP_val_one = CHP_one
                prev_CHP_val_two = CHP_two
            
        
    data_CHP_dual.set_value(index,'waste_energy', waste_energy)        
    data_CHP_dual.set_value(index,'buffer_energy_now',buffer_energy)


check_dual_CHP_behaviour = data_CHP_dual
check_dual_CHP_behaviour = check_dual_CHP_behaviour \
                        .drop(['Cons_percentage','cons_kWh', 'waste_energy'], 1)
ax = check_dual_CHP_behaviour.plot(legend=None)
fig = ax.get_figure()
fig.savefig("dual_CHP_behaviour.png", dpi=400)


print "\n\nChecking how much each unit needs to turn on or off"
temp_df = data_CHP_dual
on_time = 0
CHP_on = False
counter = [0,0,0,0,0,0,0,0,0,0,0]
longterm = 0
count = 0
for index, row in temp_df.iterrows():
    if row['CHP_prod_one'] > 0:  #change to 'CHP_prod_two' if you want to see
                                 #the numbers for the second unit
        if CHP_on != True:
            CHP_on = True
        on_time += 1
        count += 1
    else:
        if CHP_on:
            CHP_on = False
            #print row['UTC'], ": CHP has turned off after ", on_time, " hours"
            temp = on_time
            if on_time > 10:
                temp = 11
                longterm += on_time
            counter[temp-1] += 1
            on_time = 0

for i in range(len(counter)):
    print i+1, " hours: ", counter[i], "x"
print longterm
print "sum: ", sum(counter)
print "total working hours = ", count, "\trelative = ", (count/8760.0*100), "%"


