import copy
from itertools import groupby

class Accelerator:
    def __init__(self, pg, startRow) -> None:
        self.pg = pg
        self.startRow = startRow
        self.endRow = self.startRow + self.pg.n - 1

    def move(self, newStartRow):
        self.startRow = newStartRow
        self.endRow = self.startRow + self.pg.n - 1
    
class ReconfigurableFabric:
    def __init__(self, numRows, numCols):
        self.numRows = numRows
        self.numCols = numCols

        self.accelerators = {} #*keys will be branch instruction address of accelerator
        
        self.slots = []
        for i in range(numRows):
            innerArray = [None] * numCols #m columns
            self.slots.append(innerArray) #n rows

    def addAccelerator(self, startRow, accID, pg):
        acc = Accelerator(pg, startRow)
        self.accelerators[accID] = acc

        for i in range(startRow, startRow + pg.n):
            for j in range(pg.m):
                self.slots[i][j] = accID

    def removeAccelerator(self, accID):
        acc = self.accelerators[accID]

        for i in range(acc.startRow, acc.startRow + acc.pg.n):
            for j in range(acc.pg.m):
                self.slots[i][j] = None

        del self.accelerators[accID]

    def replaceAccelerators(self, accsToRemove, accToAddID, accToAddPG):
        for accID in accsToRemove:
            self.removeAccelerator(accID)
        
        rowUseds = []
        for row in self.slots:
            rowUsed = False
            for slot in row:
                if slot != None:
                    rowUsed = True
                    break
            
            rowUseds.append(rowUsed)

        rowUseds = [list(g) for _, g in groupby(rowUseds)]
        rowUseds = [(g[0], len(g)) for g in rowUseds]
        rowsRequired = accToAddPG.n

        startRow = 0
        spaceFound = False
        for used, numRows in rowUseds:
            if not used and numRows >= rowsRequired:
                spaceFound = True
                break
            startRow += numRows
        
        if spaceFound:
            self.addAccelerator(startRow, accToAddID, accToAddPG)
            return self.compactGrid()
        else:
            compactingCost = self.compactGrid()
            nextFreeRow = self.findNextFreeRow()
            self.addAccelerator(nextFreeRow, accToAddID, accToAddPG)
            return compactingCost

    def findNextFreeRow(self):
        for rowNum, row in enumerate(self.slots):
            free = True
            for col in row:
                if col != None:
                    free = False
            if free:
                return rowNum
        
        return False #no more free rows

    def findAccleratorInRow(self, rowNum):
        for accID, acc in self.accelerators.items():
            if rowNum >= acc.startRow and rowNum <= acc.endRow:
                return accID
        
        return False #no accelerator in this row

    def findNextOccupiedRowAfter(self, afterRow):
        for rowNum in range(afterRow+1, len(self.slots)):
            for accID, acc in self.accelerators.items():
                if rowNum >= acc.startRow and rowNum <= acc.endRow:
                    return rowNum, accID

        return False, False #no further occupied rows

    
    def compactGrid(self):
        compactingMoves = 0
        nextFreeRow = self.findNextFreeRow()        
        if nextFreeRow == False:
            return compactingMoves, False
            
        nextOccupiedRow, occupyingAccID = self.findNextOccupiedRowAfter(nextFreeRow)
        while nextOccupiedRow != False:
            compactingMoves += self.moveAccelerator(occupyingAccID, nextFreeRow)
            nextFreeRow = self.findNextFreeRow()
            if nextFreeRow == False:
                return compactingMoves, False
            
            nextOccupiedRow, occupyingAccID = self.findNextOccupiedRowAfter(nextFreeRow)
        
        return compactingMoves

    def moveAccelerator(self, accID, newStartRow):
        accToMove = self.accelerators[accID]
        currRow = newStartRow
        for rowNum in range(accToMove.startRow, accToMove.endRow + 1):
            self.slots[currRow] = copy.deepcopy(self.slots[rowNum])
            currRow += 1

        accToMove.move(newStartRow)
        self.accelerators[accID] = accToMove #*reassign in case a new object was created

        return self.numCols * (accToMove.endRow + 1 - accToMove.startRow) #returns num slots moved

    def extraRowsRequired(self, rowsRequired):
        return max(0,(self.findNextFreeRow() + rowsRequired - self.numRows))

#*process for adding accelerators
#*1. Get next free row
#*2. Check if accelerator will fit in space between next free row and end of reconfigurable fabric
#*3. If yes, just use addAcclerator()
#*4 If not, use replaceAccelerators() - will ensure grid is compacted at the end of replacement
#* Note: returned value is the number of PR slots which need to be written on move
#* multiply this by time needed to move one PR slot, then add time needed to add new accelerator, then add reconfiguration starting time to get penalty