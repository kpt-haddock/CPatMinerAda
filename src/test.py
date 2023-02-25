class Apple:
    label: str

    def __init__(self, label: str):
        self.label = label


class Fruit:
    apple: Apple

    def __init__(self, apple: Apple):
        self.apple = apple
        apple.label = 'Golden Delicious'

apple: Apple = Apple('Gala')

print(apple.label)
fruit: Fruit = Fruit(apple)
print(fruit.apple.label)
print(apple.label)

names = ['john', 'paul', 'bob']
print(names)
names.append('joe')
print(names)

test_string = 'This is a test, and it is testing good!'
test_string_banana_index = test_string.rfind('banana')
print('test_string_banana_index: {}'.format(test_string_banana_index))

print(round(5.49))
print(round(5.51))