from .flow_base import FlowBase
import util.prompts as prompts
import matplotlib.pyplot as plt
import networkx as nx

class VisualizeData(FlowBase):
    prompt_text = "Display data."

    def run(self):
        while True:
            options = ['Revenue', 'Friendship', 'finished']
            descriptions = ['Display monthly revenue for 2019', 'Display friendship graph', 'Exit']
            option = prompts.select_from_list(options, descriptions, 'What would you like to do?')

            if option == 'Revenue':
                x = []
                y = []
                l = []

                with self.connection.cursor() as cursor:
                    cursor.execute('SELECT amount_paid, trans_date FROM coin_purchases')
                    l = cursor.fetchall()
                    l.sort(key=lambda la: (la[1]))

                last_purchase_year = l[-1][1].year

                for i in range(2019, last_purchase_year):
                    for j in range(1, 13):
                        s = str(i) + '-' + str(j)
                        x.append(s)

                for month in x:
                    total = 0
                    for purchase in l:
                        if int(month[0:4]) == purchase[1].year and int(month[5:]) == purchase[1].month:
                            total += purchase[0]

                    y.append(total)

                plt.title('Revenue per Month')
                plt.xlabel('Month')
                plt.ylabel('Revenue (Coins)')
                plt.xticks(rotation=45)

                plt.plot(x, y, color='r')
                plt.show()

            elif option == 'Friendship':
                l = []
                with self.connection.cursor() as cursor:
                    cursor.execute('SELECT requester_username, requestee_username FROM friends')
                    l = cursor.fetchall()

                G = nx.Graph()

                for (f1, f2) in l:
                    G.add_edge(f1, f2)

                nx.draw(G, with_labels=True, node_size=1000, node_color='red')
                plt.show()

            else:
                return None