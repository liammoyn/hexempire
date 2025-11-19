import board as b
import numpy as np
import random
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from gamerunner import ComputerGameRunner
from players.objective_player import ObjectivePlayer, defaultPreferences, getPreferenceIdFromVector

def runGameHelper(gameRunnerInstance):
	method = getattr(gameRunnerInstance, "runGame")
	return method()

class EvolutionRunner():
	MAX_EPOCHS = 32
	POPULATION_SIZE = 64
	VECTOR_LENGTH = 9

	def __init__(self):
		self.best = []


	def runEvolution(self):
		"""
		Initialization
			- Each ObjectivePlayer takes in a len 8 array of floats 0-1 for their preferences
			- Start with completely random values
		Evaluation
			- Every player plays on a random set seed
			- Every player plays each starting spot
		Mutation
			- Gausian mutation of each parameter, reduce mutation rate over time
		Selection
			- Use top 50%, mutate twice to replace
		"""

		population = self.initalizePopulationVectors()
		for i in range(1, self.MAX_EPOCHS + 1):
			roundStart = time.time()
			vectorScores = self.evaluateVectors(population)
			print(f"Round {i} took {int(time.time() - roundStart)} seconds")

			sortedVectorWithScores = sorted(zip(population, vectorScores), key=lambda x: x[1], reverse=True)

			for j in range(2):
				v, s = sortedVectorWithScores[j]
				print(f"[{i}] ({s}) = {getPreferenceIdFromVector(v)}")

			topVectors = list(map(lambda l: l[0], sortedVectorWithScores[:int(len(sortedVectorWithScores)/2)]))

			nextPopulation = self.getMutatedChildren(topVectors, i)
			population = nextPopulation


	def initalizePopulationVectors(self) -> list[list[float]]:
		"""
		Return a list of initial vectors
		"""
		randomVectors = [ [ random.random() for _ in range(self.VECTOR_LENGTH) ] for _ in range(self.POPULATION_SIZE - 1) ]
		randomVectors.insert(random.randint(0, len(randomVectors)), defaultPreferences)
		return randomVectors

	def evaluateVectors(self, vectors) -> list[float]:
		"""
		For a given preference vector, assign a relative score to each vector based on performance

		TODO: Each vector should play each corner, but with different opponents
		"""
		idToVector = { getPreferenceIdFromVector(v): v for v in vectors }
		gameAssignments = list(range(len(vectors)))
		random.shuffle(gameAssignments)

		seed = int(time.time() * 256)
		board = b.initializeBoard(12, 8, seed=seed)
		print(f"Running round with seed: ({seed})")

		# q1 = int(len(gameAssignments) * 0.25)
		# q2 = int(len(gameAssignments) * 0.5)
		# q3 = int(len(gameAssignments) * 0.75)
		# groups = [
		# 	gameAssignments[: q1],
		# 	gameAssignments[q1 : q2],
		# 	gameAssignments[q2 : q3],
		# 	gameAssignments[q3 :],
		# ]
		# print(f"{len(groups[0])} {len(groups[1])} {len(groups[2])} {len(groups[3])}")

		# for _ in range(4):
		# 	# TODO: Check this works
		# 	random.shuffle(groups[1])
		# 	random.shuffle(groups[2])
		# 	random.shuffle(groups[3])
		# 	for i in range(len(gameAssignments) / 4):
		# 		players = [ ObjectivePlayer(idx, groups[idx][i]) for idx in range(4) ]
		# 		gameRunner = ComputerGameRunner(players, board)
		# 		vectorAssignmentIds.append(orderedVectorIds)
		# 		gameRunners.append(gameRunner)


		vectorAssignmentIds = []
		gameRunners = []
		for i in range(int(len(vectors) / 4)):
			gameVectorIds = gameAssignments[i * 4 : (i + 1) * 4]
			for gameNum in range(4):
				orderedVectorIds = gameVectorIds[-gameNum:] + gameVectorIds[:-gameNum]
				players = [ ObjectivePlayer(idx, vectors[vectorIdx]) for idx, vectorIdx in enumerate(orderedVectorIds) ]
				gameRunner = ComputerGameRunner(players, board)
				vectorAssignmentIds.append(orderedVectorIds)
				gameRunners.append(gameRunner)


		finalScores = [ 0 for _ in vectors ]
		with ProcessPoolExecutor() as executor:
			gameResults = executor.map(runGameHelper, gameRunners)

			resultsWithAssignments = zip(gameResults, vectorAssignmentIds)
			for gameResult, vectorAssignment in resultsWithAssignments:
				for playerId, score in gameResult.items():
					vectorId = vectorAssignment[playerId]
					finalScores[vectorId] += score

		finalScores = [ s / 4 for s in finalScores ]
		return finalScores

	def getMutatedChildren(self, seedVectors, roundNum) -> list[list[float]]:
		"""
		Given a list of initial vectors, apply mutations to create children up to self.POPULATION_SIZE
		"""
		newVectors = []
		for i in range(self.POPULATION_SIZE):
			seedVector = seedVectors[i % len(seedVectors)]
			childVector = self.mutateVector(seedVector, roundNum)
			newVectors.append(childVector)
		return newVectors

	def mutateVector(self, seedVector, roundNum) -> list[float]:
		scale = 0.1 / roundNum
		newVector = []
		for v in seedVector:
			mutation = np.random.normal(scale=scale)
			newValue = max(min(v + mutation, 1), 0)
			newVector.append(newValue)
		return newVector




if __name__ == '__main__':
	evolutionRunner = EvolutionRunner()
	evolutionRunner.runEvolution()