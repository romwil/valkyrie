import { createSlice, PayloadAction } from '@reduxjs/toolkit'
import { Company } from '../types'

interface CompaniesState {
  selectedCompany: Company | null
  searchQuery: string
}

const initialState: CompaniesState = {
  selectedCompany: null,
  searchQuery: '',
}

const companiesSlice = createSlice({
  name: 'companies',
  initialState,
  reducers: {
    setSelectedCompany: (state, action: PayloadAction<Company | null>) => {
      state.selectedCompany = action.payload
    },
    setSearchQuery: (state, action: PayloadAction<string>) => {
      state.searchQuery = action.payload
    },
  },
})

export const { setSelectedCompany, setSearchQuery } = companiesSlice.actions
export default companiesSlice.reducer
