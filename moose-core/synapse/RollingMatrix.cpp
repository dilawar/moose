/**********************************************************************
** This program is part of 'MOOSE', the
** Messaging Object Oriented Simulation Environment.
**           Copyright (C) 2016 Upinder S. Bhalla. and NCBS
** It is made available under the terms of the
** GNU Lesser General Public License version 2.1
** See the file COPYING.LIB for the full notice.
**********************************************************************/

#include <vector>
#include <iostream>
#include <cassert>
using namespace std;

#include "RollingMatrix.h"


RollingMatrix::RollingMatrix()
    : nrows_(0), ncolumns_(0), currentStartRow_(0)
{;}


RollingMatrix::~RollingMatrix()
{;}

RollingMatrix& RollingMatrix::operator=( const RollingMatrix& other )
{
    nrows_ = other.nrows_;
    ncolumns_ = other.ncolumns_;
    currentStartRow_ = other.currentStartRow_;
    rows_ = other.rows_;
    return *this;
}


void RollingMatrix::resize( size_t nrows, size_t ncolumns )
{
    rows_.resize( nrows );
    nrows_ = nrows;
    ncolumns_ = ncolumns;
    for ( size_t i = 0; i < nrows; ++i )
    {
        rows_[i].resize( ncolumns, 0.0 );
    }
    currentStartRow_ = 0;
}

double RollingMatrix::get( size_t row, size_t column ) const
{
    size_t index = (row + currentStartRow_ ) % nrows_;
    return rows_[index][column];
}

void RollingMatrix::sumIntoEntry( double input, size_t row, size_t column )
{
    size_t index = (row + currentStartRow_ ) % nrows_;
    SparseVector& sv = rows_[index];
    sv[column] += input;
}

void RollingMatrix::sumIntoRow( const vector< double >& input, size_t row )
{
    size_t index = (row + currentStartRow_) % nrows_;
    SparseVector& sv = rows_[index];

    for (size_t i = 0; i < input.size(); ++i )
        sv[i] += input[i];
}


double RollingMatrix::dotProduct( const vector< double >& input,
                                  size_t row, size_t startColumn ) const
{
    /// startColumn is the middle of the kernel.
    size_t index = (row + currentStartRow_) % nrows_;
    const SparseVector& sv = rows_[index];
    size_t i2 = input.size()/2;
    size_t istart = (startColumn >= i2) ? 0 : i2-startColumn;
    size_t colstart = (startColumn <= i2) ? 0 : startColumn - i2;
    size_t iend = (sv.size()-startColumn > i2 ) ? input.size() :
                        i2 - startColumn + sv.size();

    // if ( iend >= istart ) cout << startColumn << i2 << istart << iend << colstart << "\n";
    double ret = 0;
    for (size_t i = istart, j = 0; i < iend; ++i, ++j )
        ret += sv[j + colstart] * input[i];

    /*
    double ret = 0;
    if ( input.size() + startColumn <= sv.size() ) {
    	for (size_t i = 0; i < input.size(); ++i )
    		ret += sv[i + startColumn] * input[i];
    } else if ( sv.size() > startColumn ) {
    	size_t end = sv.size() - startColumn;
    	for (size_t i = 0; i < end; ++i )
    		ret += sv[i + startColumn] * input[i];
    }
    */
    return ret;
}

void RollingMatrix::correl( vector< double >& ret,
                            const vector< double >& input, size_t row) const

{
    if ( ret.size() < ncolumns_ )
        ret.resize( ncolumns_, 0.0 );
    for ( size_t i = 0; i < ncolumns_; ++i )
    {
        ret[i] += dotProduct( input, row, i );
    }
}

void RollingMatrix::zeroOutRow( size_t row )
{
    size_t index = (row + currentStartRow_) % nrows_;
    rows_[index].assign( rows_[index].size(), 0.0 );
}

void RollingMatrix::rollToNextRow()
{
    if ( currentStartRow_ == 0 )
        currentStartRow_ = nrows_ - 1;
    else
        currentStartRow_--;
    zeroOutRow( 0 );
}
